"""Local owner/SYSTEM storage protection; existing unsafe data requires explicit repair."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import stat
import time


class PrivateStorageUnavailable(RuntimeError):
    pass


def safe_path(value):
    path = Path(value)
    if not path.is_absolute() or path.drive.startswith("\\\\"):
        raise PrivateStorageUnavailable("Private storage requires an absolute local directory.")
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise PrivateStorageUnavailable("Linked private storage is not supported.")
    return path.resolve()


@lru_cache(maxsize=1)
def windows():
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    api.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer), ctypes.POINTER(pointer)]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(pointer)]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.POINTER(pointer), ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [pointer, wintypes.DWORD,
        wintypes.DWORD, ctypes.POINTER(pointer), ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorDacl.argtypes = [pointer, ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(pointer), ctypes.POINTER(wintypes.BOOL)]
    api.GetSecurityDescriptorControl.argtypes = [pointer, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    api.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    api.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, pointer, pointer, pointer, pointer]
    api.SetNamedSecurityInfoW.restype = wintypes.DWORD
    api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, pointer, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [pointer]
    return api, kernel


def sid_string(sid):
    api, kernel = windows()
    result = ctypes.c_void_p()
    if not api.ConvertSidToStringSidW(sid, ctypes.byref(result)):
        raise PrivateStorageUnavailable("Windows identity verification failed.")
    try:
        return ctypes.wstring_at(result)
    finally:
        kernel.LocalFree(result)


@lru_cache(maxsize=1)
def current_sid():
    api, kernel = windows()
    token = wintypes.HANDLE()
    if not api.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise PrivateStorageUnavailable("Windows identity verification failed.")
    try:
        size = wintypes.DWORD()
        api.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not api.GetTokenInformation(token, 1, buffer, size.value, ctypes.byref(size)):
            raise PrivateStorageUnavailable("Windows identity verification failed.")
        return sid_string(ctypes.c_void_p.from_buffer(buffer).value)
    finally:
        kernel.CloseHandle(token)


def acl_snapshot(path):
    api, kernel = windows()
    dacl, descriptor = ctypes.c_void_p(), ctypes.c_void_p()
    if api.GetNamedSecurityInfoW(str(path), 1, 4, None, None, ctypes.byref(dacl), None, ctypes.byref(descriptor)):
        raise PrivateStorageUnavailable("Private storage permissions cannot be inspected.")
    try:
        control, revision = wintypes.WORD(), wintypes.DWORD()
        if not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)) or not dacl.value:
            raise PrivateStorageUnavailable("Private storage has no usable access controls.")
        # ACL header stores AceCount at byte four; each ordinary ACE has SID at byte eight.
        count = ctypes.c_uint16.from_address(dacl.value + 4).value
        entries = []
        for index in range(count):
            ace = ctypes.c_void_p()
            if not api.GetAce(dacl, index, ctypes.byref(ace)):
                raise PrivateStorageUnavailable("Private storage permissions cannot be inspected.")
            kind = ctypes.c_ubyte.from_address(ace.value).value
            flags = ctypes.c_ubyte.from_address(ace.value + 1).value
            if kind != 0:
                entries.append({"kind": kind})
            else:
                entries.append({"kind": 0, "flags": flags,
                    "mask": ctypes.c_uint32.from_address(ace.value + 4).value,
                    "sid": sid_string(ace.value + 8)})
        text = ctypes.c_void_p()
        if not api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 4, ctypes.byref(text), None):
            raise PrivateStorageUnavailable("Private storage permissions cannot be recorded.")
        try:
            sddl = ctypes.wstring_at(text)
        finally:
            kernel.LocalFree(text)
        return {"sddl": sddl, "protected": bool(control.value & 0x1000), "entries": entries}
    finally:
        kernel.LocalFree(descriptor)


def replace_acl(path, sddl):
    api, kernel = windows()
    descriptor, dacl = ctypes.c_void_p(), ctypes.c_void_p()
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
        raise PrivateStorageUnavailable("Invalid private storage permission plan.")
    try:
        present, defaulted = wintypes.BOOL(), wintypes.BOOL()
        if not api.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)) or not present:
            raise PrivateStorageUnavailable("Invalid private storage permission plan.")
        control, revision = wintypes.WORD(), wintypes.DWORD()
        if not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)):
            raise PrivateStorageUnavailable("Invalid private storage permission plan.")
        flags = 4 | (0x80000000 if control.value & 0x1000 else 0x20000000)
        if api.SetNamedSecurityInfoW(str(path), 1, flags, None, None, dacl, None):
            raise PrivateStorageUnavailable("Private storage permissions could not be applied.")
    finally:
        kernel.LocalFree(descriptor)


def verify_private(path):
    path = safe_path(path)
    if os.name != "nt":
        return path.stat().st_uid == os.getuid() and not stat.S_IMODE(path.stat().st_mode) & 0o077
    snapshot = acl_snapshot(path)
    allowed = {current_sid(), "S-1-5-18"}
    entries = snapshot["entries"]
    exact = len(entries) == 2 and {
        e.get("sid") for e in entries} == allowed and all(e["kind"] == 0 and not e["flags"] & 8
        and e["mask"] & 0x1F01FF == 0x1F01FF for e in entries)
    return exact and (not path.is_dir() or snapshot["protected"] or verify_private(path.parent))


def protect(path):
    path = safe_path(path)
    if os.name == "nt":
        flags = "OICI" if path.is_dir() else ""
        replace_acl(path, f"D:P(A;{flags};FA;;;{current_sid()})(A;{flags};FA;;;SY)")
    else:
        path.chmod(0o700 if path.is_dir() else 0o600)
    if not verify_private(path):
        raise PrivateStorageUnavailable("Private storage protection verification failed.")


def private_directory(path, *, deadline=None):
    path = safe_path(path)
    if deadline is not None and time.monotonic() >= deadline:
        raise PrivateStorageUnavailable("Private storage protection deadline expired.")
    fresh = not path.exists() or path.is_dir() and not any(path.iterdir())
    path.mkdir(parents=True, exist_ok=True)
    if fresh:
        protect(path)
    elif not verify_private(path):
        raise PrivateStorageUnavailable("Existing private storage needs explicitly authorized permission repair.")
    return path


def permission_plan(root):
    root = safe_path(root)
    paths = [root, *sorted(root.rglob("*"))]
    records = []
    for path in paths:
        path = safe_path(path)
        if not path.is_relative_to(root):
            raise PrivateStorageUnavailable("Permission plan escapes the selected directory.")
        info = path.stat()
        records.append({"relative": path.relative_to(root).as_posix(), "directory": path.is_dir(),
            "bytes": info.st_size if path.is_file() else None,
            "mtime": info.st_mtime_ns if path.is_file() else None, "acl": acl_snapshot(path)})
    return {"version": 1, "root": str(root), "owner": current_sid(), "records": records}


def apply_plan(plan, *, authorization_reference, quiesced=False):
    if not authorization_reference or not quiesced or plan.get("owner") != current_sid():
        raise PrivateStorageUnavailable("Permission repair requires explicit authorization and quiesced writers.")
    root = safe_path(plan["root"])
    # Validate the entire plan before the first change; preserve it for ACL rollback.
    if permission_plan(root) != plan:
        raise PrivateStorageUnavailable("Permission plan changed; regenerate and obtain approval again.")
    for record in plan["records"]:
        protect(safe_path(root / record["relative"]))


def rollback_plan(plan, *, authorization_reference, quiesced=False):
    if not authorization_reference or not quiesced or plan.get("owner") != current_sid():
        raise PrivateStorageUnavailable("Permission rollback requires explicit authorization and quiesced writers.")
    root = safe_path(plan["root"])
    current = permission_plan(root)
    expected = [{k: v for k, v in r.items() if k != "acl"} for r in plan["records"]]
    actual = [{k: v for k, v in r.items() if k != "acl"} for r in current["records"]]
    if actual != expected:
        raise PrivateStorageUnavailable("Storage changed; permission rollback must be reviewed.")
    for record in plan["records"]:
        replace_acl(safe_path(root / record["relative"]), record["acl"]["sddl"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--authorization-reference")
    parser.add_argument("--quiesced", action="store_true")
    args = parser.parse_args()
    try:
        if args.apply and args.rollback:
            raise PrivateStorageUnavailable("Choose repair or rollback, not both.")
        if args.apply or args.rollback:
            if not args.plan or not args.expected_sha256:
                raise PrivateStorageUnavailable("Apply requires a pinned retained permission plan.")
            encoded = args.plan.read_bytes()
            if hashlib.sha256(encoded).hexdigest() != args.expected_sha256:
                raise PrivateStorageUnavailable("Permission plan hash mismatch.")
            plan = json.loads(encoded)
            if safe_path(plan["root"]) != safe_path(args.root):
                raise PrivateStorageUnavailable("Permission plan target mismatch.")
            action = rollback_plan if args.rollback else apply_plan
            action(plan, authorization_reference=args.authorization_reference, quiesced=args.quiesced)
        else:
            plan = permission_plan(args.root)
            if args.plan:
                if args.plan.absolute().is_relative_to(safe_path(args.root)):
                    raise PrivateStorageUnavailable("Keep the retained permission plan outside the repair target.")
                parent = private_directory(args.plan.absolute().parent)
                target = parent / args.plan.name
                with target.open("x", encoding="utf-8") as output:
                    json.dump(plan, output, sort_keys=True)
                protect(target)
        print(json.dumps({"status": "ROLLED_BACK" if args.rollback else "APPLIED" if args.apply else "DRY_RUN",
            "files": len(plan["records"]), "private": verify_private(safe_path(args.root))}))
        return 0
    except (OSError, ValueError, KeyError, PrivateStorageUnavailable) as exc:
        print(json.dumps({"status": "BLOCKED", "exception_class": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
