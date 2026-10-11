# Hardware baseline before Windows cleanup

Captured 2026-10-06. This is safe hardware metadata for later Ollama/Codex planning. No Ollama installation or model download was performed.

| Item | Observed value |
|---|---|
| CPU | AMD Ryzen 5 3500X 6-Core Processor |
| Cores / logical processors | 6 / 6 |
| Total RAM | 15.91 GiB |
| System manufacturer / model | Gigabyte Technology Co., Ltd. / B550 AORUS PRO AC |
| GPU | AMD Radeon RX 6700 XT |
| Dedicated VRAM, driver-reported | 12,868,124,672 bytes, approximately 11.98 GiB (12 GiB nominal) |
| GPU driver | 32.0.21045.5002 |
| Windows | Windows 11 Pro, version 10.0.26200 |
| Windows architecture | 64-bit; AMD64 processor architecture |
| NVIDIA tooling | `nvidia-smi` unavailable; installed GPU is AMD |

CPU, RAM, GPU, driver and Windows fields came from `Win32_Processor`, `Win32_ComputerSystem`, `Win32_VideoController` and `Win32_OperatingSystem`. The matching AMD display-driver registry entry's 64-bit `HardwareInformation.qwMemorySize` supplied the dedicated-memory figure. CIM's 32-bit `AdapterRAM` reported 4,293,918,720 bytes and truncates near 4 GiB; do not use that value to size a model.

After Windows and ALFRED recovery, install the appropriate supported GPU driver and recheck usable VRAM and Ollama's actual acceleration/backend support. Recorded capacity does not prove compatibility or available memory after driver/OS overhead. Choose and test a model then, keeping room for ALFRED, the IDE, context and model runtime. Model selection and downloads remain deferred.

See [the post-reinstall hybrid plan](OLLAMA_CODEX_HYBRID_PLAN.md) and [agent tooling reinstall inventory](AGENT_TOOLS_REINSTALL.md).
