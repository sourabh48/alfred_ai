# Human acceptance checks

Record the ALFRED executable SHA-256, Windows version, browser/version, date and
the tester's observations. Use disposable test accounts and checked synthetic or
anonymized documents. Automated browser/accessibility results do not replace
these observations.

## Windows sign-in

After saving other work, sign out and sign back into Windows normally. Do not
manually launch ALFRED first. Check that the startup entry is enabled in Windows
Startup apps and that ALFRED is already running. Open its local address, sign in
and confirm the expected data. Record any prompt, failure or manual intervention.
Registration alone is not a successful sign-in test.

## Screen reader and keyboard

Use Windows Narrator or the tester's normal screen reader with Chrome or Edge.

1. Reach sign-in, the main navigation and the main-content skip link using Tab.
   Check that each control announces an understandable name and its state.
2. Read dashboard totals and review notices. Check that the descriptions make
   clear which transactions are excluded and which amounts represent outflow.
3. Open Documents and expand a correction form. Navigate every field, enter a
   correction and wait through a live refresh. Confirm focus and input survive.
4. Save a resume, loan and credit-report correction. Confirm success/error
   feedback is announced and the saved value survives a page reload.
5. Test invalid input and an empty document queue. Check announcements, focus
   order and recovery without using a pointer.
6. Repeat the key tasks at 200% zoom and a narrow viewport. Confirm controls and
   values remain readable and reachable, including any scrolling table regions.

Record pass/fail and exact steps for each case, along with the screen reader
version. An automated absence of serious findings does not mean these passed.

## Real-document and model evidence

For each additional document, record the family/provider/layout, checked fields,
expected values, actual values and accepted corrections. Keep source files and
personal results in ignored local storage. Published evidence should contain
aggregate counts and synthetic examples only.

Model validation needs consenting users, independently observed targets and
evaluation separated by user and time. The local model audit reports sample,
quality, confidence and artifact blockers. Do not clear these gates using
duplicated samples, synthetic fits or labels computed from the input features.

## Separate PC

Follow [Windows acceptance](WINDOWS_ACCEPTANCE.md) for Fresh and Reboot phases,
then try a checked document, Settings and uninstall retention. Keep both proof
files and these manual observations. The transfer kit rejects its development
machine and mismatched executables; neither a temporary folder nor a process
restart substitutes for a separate PC and a Windows reboot.
