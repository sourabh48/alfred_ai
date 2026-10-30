# PR20 cumulative change manifest

Base: `a2274aa4daa514afe05ab58b4e4219ef18bb825f`. Retained tested checkpoint: `c28700d8da1e545441b1dec7e3292d71497ec6e7`.
Candidate: the commit containing this manifest; exact source/run closure lives in `artifacts/d4-ci-repair-20261030/checkpoint.json`.
All cumulative changed paths are listed. SHA256 hashes use LF-normalized source bytes; documentation rows omit hashes to avoid self-reference.
This is an inventory/review input, not independent approval or an executable test result.

Recompute the diff using the commands in [review package](D4_PR20_REVIEW.md).
D4 extends c287 with request-parser guards/settings, explicit parser callers and seven regression cases; no dependency/migration/package changes.

## Recovery, verification and CI (10)

| Status | Path | SHA256 (LF bytes) |
| --- | --- | --- |
| M | `.github/workflows/browser-regression.yml` | `1541c12674af89a2f12ecf277888438dfdee7a06f2b31875141e329b8ef274f1` |
| A | `scripts/browser_test_plan.py` | `a67dadd78b2655c89adfbad462ee4d06a1a32c986ef0395b4ba45e73c224acdd` |
| A | `scripts/browser_test_runner.py` | `e1de47e86de2b477291871d90bd2a2efd14c36a03fdf87b8ef156e385e2c2f60` |
| A | `scripts/native_probe_runner.py` | `caf6a68a00ca32081c07dda65c90408eb5b4f857a633c4f0b5c07adde29d06c3` |
| M | `scripts/release_recovery.py` | `ed2651b73168ece54caf5e215e97152a48fe98a2e45d8af67cb2bb1f9ebdd126` |
| M | `scripts/release_validation.py` | `d169a1163f3b5f21129a1200899b79ff4e8f65857c8f3e41c16ec5f9e13e34d2` |
| M | `scripts/run_browser_regressions.py` | `d1c8ad2c01d72d62950d430a6c057c9684aff8f6cb711a0928dbaccab7051e61` |
| A | `scripts/verify_native_backup.py` | `8e4f6981eef59993c49bf798cae6738602e5ca1a810758d133150289fbaf2378` |
| A | `scripts/verify_native_recovery.py` | `d932414d693bf2a8a8e74d71d3b42c1b918bbd21693e7317e826c9151708d308` |
| A | `scripts/verify_native_travel.py` | `5846583fb5fa3c521cbc1ac45716b10b67c6041a8117ae591c4f25f26b141733` |

## Application and UI runtime (36)

| Status | Path | SHA256 (LF bytes) |
| --- | --- | --- |
| M | `alfred_ai/durable_queue.py` | `4b9c051b0b419d05235caaf559cf8906092983130875626ff406d8be63338cd3` |
| M | `alfred_ai/native_tasks.py` | `c0d0befbd787472330b79b09fdf17f27816cb4d8492f312f7536679f231e554d` |
| A | `alfred_ai/services/api_parsing.py` | `74f76138823621890a30a7ed6ab044b6a618a47f6cd3ffea44d197f602c2ad4d` |
| M | `alfred_ai/settings.py` | `b4ba85899d649c895bcfacb9f3a3c052db355d3cf0d576f3dac741833f7d922b` |
| M | `apps/career/views.py` | `03cb5e80c9a9c9790e6d68eb050dbff4ae133ce00da48f2262a35b4c2333cbd9` |
| M | `apps/expenses/services/financial_intelligence.py` | `0dc8836cfc8fd548f84c10bab5e4ea2444aff2a0ca327cdf0c4cbb9b641ce49f` |
| M | `apps/expenses/services/statement_evidence.py` | `474f7f49f0f6115cdeffc0c219e13d5c8b7848ac337b0793e689d7d35b5b8c75` |
| M | `apps/loans/views.py` | `404895a212eda485dbebe03cb77411f7cf8b9bd0f5986df6b6f7fb4ad507582f` |
| M | `apps/ml_engine/services/persistent_memory.py` | `2363a8bb8897ad52fc276751017787d3eb30a20859e9e0d645a2d01f675a5b28` |
| M | `apps/mobility/planner_views.py` | `be0c4b67a4dc132d36a7fb5b45ffa97d45463538c983656a9be77a5c836b8ce1` |
| A | `apps/mobility/services/travel/affordability.py` | `13999944ca48d75f6fef438f694211105b2a81ca09e38224ebb7f9df951da645` |
| A | `apps/mobility/services/travel/affordability_ui.py` | `cbbb76af846c164d4af9716d03ccdaf48fa5caeb714a0c3954c7b10b80c5b31d` |
| A | `apps/mobility/services/travel/documents.py` | `c13a4e3022d8b1fce06f665fed508af0a3050b23fae9d342c6d4b5936f3fd108` |
| A | `apps/mobility/services/travel/editor.py` | `90a6cec0881d477a86f726e35ba98a8b81b24a9f5678c8fa962ecef389969ed8` |
| A | `apps/mobility/services/travel/gpx_export.py` | `e409664514c7a9ef1ca5d2fd92470cbecc9f21362539054a29ab11e3c97f8295` |
| A | `apps/mobility/services/travel/ics_export.py` | `25601adbf879d349dc4920d7c5cab3f709e6c100dbe6d99dd18c3196f29731d1` |
| A | `apps/mobility/services/travel/packing.py` | `471be43fc5d6bbea852ea7f56cc6f102bd31f6b364ff1b7f1846ffd6df360f08` |
| A | `apps/mobility/services/travel/pdf_export.py` | `eae2578f9d5cbc81259d2571b697bf13600118496a37fee305dc1d9c44ac042b` |
| A | `apps/mobility/services/travel/reminders.py` | `dda7943a5988ee3ea54c923b3f0d4d3dbd6f9b9944d5e07dc383bcbc13b7cafc` |
| A | `apps/mobility/services/travel/savings.py` | `d401ad7e97ce816493cab0a7e8124400f4a6f6d1bf5471547c8eee071faf19e2` |
| M | `apps/mobility/services/travel_conversation.py` | `56bf3fe18dba09c6565d54f500576cafb4306b69c37f0d93b6acdefca76e7ea3` |
| M | `apps/mobility/services/travel_itinerary.py` | `f763ee60965e8158dd9b17a9dd0927c825d6d298084740e2d184682c681d7a49` |
| M | `apps/mobility/services/travel_research.py` | `5e2901d06e1dc53fdf964cb374574d932dab4020f160307542c3af2c232d5d5f` |
| M | `apps/mobility/urls.py` | `3aeb5d7ac1e7813d2a5173cfdd49be744b83ab8aeb61efc077c9c890477588bd` |
| M | `apps/mobility/views.py` | `83281860ebf5b6ddb478a8ab678994ac6462c352539ad3fd7fe5bcf0f82bdf09` |
| M | `static/css/travel_planner.css` | `0d301c6dfe9e3f41ea0f39f9c190a8f22fa443f398bd3f480685793ad6ea2e0c` |
| M | `static/js/intelligence.js` | `7175ee10c88a1ed9cb0b5876915cea905d19b342e03146e2859d744cfe0d15be` |
| A | `static/js/travel_affordability.js` | `539970476acb6858231005c4502c20fabb1d40eec75285fda1ecd88c72309096` |
| A | `static/js/travel_calendar.js` | `3d2c382e2bfdae02da8b42430a513a53b229f3d9a52b7ab55e00fd1294de015e` |
| A | `static/js/travel_itinerary_editor.js` | `7eafce6fb55e877179596ea36ba6fb23fb224f34098d9214e174805cd93ce035` |
| A | `static/js/travel_packing.js` | `e96810a1ddbe850a21632b37716cb06091f2eee09165d5f6b3d6c6ad544cfb85` |
| M | `static/js/travel_planner.js` | `1fa2ab1e870349a63a947108f81a78e9970e941df3fd4c92d8338d1b22f8ac4c` |
| A | `static/js/travel_reminders.js` | `b5fe736ea01c3ec9316578b6fb74e782cdf9946f05b9ae58b55914d048121c7b` |
| M | `templates/ai_insights.html` | `5ea0cf7847c12c4590c870d7bc20f669f02b05639e979c55e9bf86c818dac537` |
| M | `templates/mobility/dashboard.html` | `8e37a2f41ea0a9a48a6a8723be304c2ff1d7880e09ad97fd8ac5cd660824bc81` |
| M | `templates/mobility/planner.html` | `cec22ceff544c43f517f4c46be272ce6df03616c0738394bf743c2b3e032e7ff` |

## Documentation (9)

| Status | Path | SHA256 (LF bytes) |
| --- | --- | --- |
| A | `docs/ALFRED_2_0_EXECUTION.md` | â€” |
| M | `docs/BACKUP_AND_RESTORE.md` | â€” |
| M | `docs/CI_PIPELINE_STATE.md` | â€” |
| A | `docs/D4_OWNER_ACCEPTANCE.md` | â€” |
| A | `docs/D4_PR20_CHANGE_MANIFEST.md` | â€” |
| A | `docs/D4_PR20_REVIEW.md` | â€” |
| M | `docs/DEVELOPMENT.md` | â€” |
| M | `docs/EXECUTION_STATE.md` | â€” |
| M | `docs/PROJECT_STATUS.md` | â€” |

## Tests and fixtures (34)

| Status | Path | SHA256 (LF bytes) |
| --- | --- | --- |
| A | `tests/browser_durations.json` | `e2c6294f81b2d51d8f2adfd8e9664457e2cacc355dd5ccfe8c4f5a5f0330bc03` |
| A | `tests/ics_parser.cjs` | `5d9d8f4bfa8dd970032d11d0bd5b0906323a6005370e18538960594d8c33492a` |
| M | `tests/test_api_session_security.py` | `96330782e78ebefecaf63fee8b238e33ad1fc7fc74a2ed68ee98bc509a6a6144` |
| M | `tests/test_browser_regression_runner.py` | `1853faab9419f64fa5a6ce057636fec6a30ce9f3f93b5c1c432fec51f1d963a7` |
| A | `tests/test_browser_test_plan.py` | `a633b6b0c514b8e600ce3ae9f200087d2a1dd9044a6c7fb238fd04911376134b` |
| A | `tests/test_browser_test_runner.py` | `facbfb9fd14da417cb2a5edf4a6225fbe2fc096e38895298e66a12ec42b131bd` |
| M | `tests/test_document_review_browser.py` | `2b6a9c22a931d5dfbcf01440c8bfda37f59f669bac60260d4773b98a3d8c6cc6` |
| M | `tests/test_live_ui_contracts.py` | `1d8c641c3b4637a4285d5fc7770ad857755f9f15be767cabd96e2849062b749e` |
| M | `tests/test_memory_privacy.py` | `a8ec39078b3756513653f2a79da9e1b250667ef4a939deeb96ff056874941f4d` |
| A | `tests/test_native_probe_runner.py` | `c83a9ab1a6bafefd462b8f7fe8c48034487659c59536aff6f342f6b102dcb22c` |
| M | `tests/test_native_runtime.py` | `10436ba75603e3515a5b599359f0691353c75c0a0bd472ba9c7426eeb294b8d2` |
| M | `tests/test_persistent_memory.py` | `58c5aed4084d7ffc7b22b9fe7ac0d4ea60f42e1897af7bf7efc53949fa346fff` |
| M | `tests/test_release_gate.py` | `81bf3051074330426a85bb24055bab4bc7b25a4565e46cec57696cf510901b46` |
| M | `tests/test_release_recovery.py` | `fd6b2e7a44e64f4abdc3e4b10b67c1bb04868c8feabba3cdd4a0227b17e82851` |
| M | `tests/test_release_validation.py` | `a6a6010bae3a7769457a862fa79d9c9eeb37ed13718038f88e1317e5746a9ae6` |
| A | `tests/test_travel_affordability.py` | `6b2bb27cb87569d86a8b488c3a216e003da9d40c512b70fa38cc878f18866503` |
| A | `tests/test_travel_affordability_ui.py` | `2e6dd54db6eda6e8beaf7eee7e64309962265b6b6b0558749e680bf6f5875d2c` |
| M | `tests/test_travel_candidate_pool.py` | `b51a9636d67b4ed71e37dd0413e64cdfa75ee680b40e057130820e5f71574923` |
| A | `tests/test_travel_documents.py` | `d8e7854bef3d6505d92e6355a7a6f69dc4e438e6f51d45abaa209aeeefabfff4` |
| A | `tests/test_travel_end_to_end.py` | `8d2605360b136f032f9ee22059a7fa92baaba0acd1583bb8ae74219fc0f74562` |
| A | `tests/test_travel_export_integration.py` | `34a6f7b02b4cb62df829f05f6746154b703fcbcfd4a865e05b145ef86dc8c3b7` |
| A | `tests/test_travel_financial_reconciliation.py` | `9ff409846cf2ad0695acb4d7a85881c114523c6f0be9d57d92bbfa51c39af7c7` |
| A | `tests/test_travel_gpx_export.py` | `d7792ce9e76c98603e4add874773a9c5de29e97f4ca2aa6ea2aad1ffdcda135a` |
| A | `tests/test_travel_ics_export.py` | `35936a7af32053899034cec1edf3018d60800d77a7e599ae9808811c2e445ddb` |
| A | `tests/test_travel_itinerary_editor.py` | `3e6fade2f80c1ac34dffe0ea8d5bd7a07b8ec6e594fbc8a803e10ecaeb0f1f09` |
| M | `tests/test_travel_multistop.py` | `cd575284c2f9fd2084f4f0d3153c475e3d87e2e8e7059f3910b297bc18fc12bf` |
| A | `tests/test_travel_packing.py` | `c7157f0b929e5d6ebbb04ed7f9fe354ed232be1b487235543f558a241531e5c4` |
| A | `tests/test_travel_pdf_export.py` | `06e7e3e393f0ab9774c8f149757aa64557d5d9d69de954cd25731dc5b0e9e007` |
| A | `tests/test_travel_reminders.py` | `c6483ade7821750c05b79aabb9b7e3acf4ff48d146ef9674c9266841dc22368c` |
| A | `tests/test_travel_savings.py` | `8c7931333fcb019f6054e424d34d64d5c4b9f7ed51cb9353d7f74f3d05860a48` |
| A | `tests/test_travel_security.py` | `fffab487cb08de8a67f15bedc5d239abab637a672137f54d8d54ede4c90e2b04` |
| M | `tests/test_upload_limits.py` | `cf1c1a7a7e797037bfea585270bc222d21bf0510f4484ddeb24206432f20ef19` |
| M | `tests/test_user_data_browser.py` | `1856c0467e61d391b4bd9977e8bede22654e172d6149743bdc22a19d69ed9361` |
| A | `tests/travel_persistence_support.py` | `ce516b0c3b2f1c9dcb5fe818139b44c0a6760102f6c818f8ef4e9cb65b9d7b11` |
