"""Exercise the chat planner and durable jobs in an isolated native data folder.

Uses synthetic local user data and real public weather research. Never opens
the checkout's or installed application's private database.
"""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import requests
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable",type=Path)
    parser.add_argument("--report",type=Path,default=ROOT/"artifacts"/"ops"/"travel-runtime-verification.json")
    args=parser.parse_args()
    report_path=args.report.resolve()
    data = ROOT / "artifacts" / "travel-runtime" / uuid.uuid4().hex[:10]
    data.mkdir(parents=True)
    report = {"data_dir":str(data), "executable":str(args.executable or sys.executable), "passed":False, "checks":{}}
    prefix = [str(args.executable.resolve())] if args.executable else [sys.executable, str(ROOT/"alfred_native.py")]
    def command(action):
        environment=os.environ.copy()
        if args.executable:
            environment.pop("PYTHONHOME",None)
            environment.pop("PYTHONPATH",None)
            system=Path(os.environ.get("SystemRoot","C:/Windows"))
            environment["PATH"]=os.pathsep.join(map(str,(system/"System32",system)))
        result = subprocess.run([*prefix, action, "--data-dir",str(data),"--port","8045","--no-browser"],
                                capture_output=True,text=True,timeout=240,env=environment)
        assert result.returncode == 0, (action,result.stdout,result.stderr)
    try:
        command("start")
        from alfred_native import configure, read_state
        configure(data)
        from django.contrib.auth import get_user_model
        from django.db import connections
        from django.utils import timezone
        from datetime import timedelta
        from apps.mobility.models import TravelPlanningSession
        from apps.mobility.services.travel_research import queue_research
        get_user_model().objects.create_user("travel_runtime_probe",password="SyntheticLocalTest123!",city="Bengaluru")
        base=f"http://127.0.0.1:{read_state(data)['port']}"
        client=requests.Session(); client.trust_env=False
        client.get(base+"/login/",timeout=15).raise_for_status()
        def post(path, body, form=False):
            headers={"X-CSRFToken":client.cookies["csrftoken"],"Referer":base+path}
            response=client.post(base+path,headers=headers,timeout=20,allow_redirects=False,**({"data":body} if form else {"json":body}))
            assert response.status_code in {200,201,302}, (path,response.status_code,response.text[:300])
            return response.json() if not form else None
        post("/login/",{"username":"travel_runtime_probe","password":"SyntheticLocalTest123!"},True)
        session=post("/api/mobility/planner/sessions/",{})
        endpoint=f"/api/mobility/planner/sessions/{session['id']}/"
        today=timezone.localdate()
        post(endpoint,{"text":f"I have holidays from {today+timedelta(days=4)} to {today+timedelta(days=7)}. Budget ₹15,000. Mountains and photography. Bike trip."})
        began=time.monotonic()
        queued=post(endpoint,{"text":"Yes use that"})
        report["checks"]["request_handoff_seconds"]=round(time.monotonic()-began,3)
        assert queued["research"]
        def await_ready():
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                response=client.get(base+endpoint,timeout=15);response.raise_for_status();payload=response.json()
                if payload["research"]["status"] == "ready": return payload
                assert payload["research"]["status"] != "failed",payload["research"]["error"]
                time.sleep(1)
            raise AssertionError("Research did not complete in three minutes")
        ready=await_ready()
        assert 2 <= len(ready["candidates"]) <= 3
        report["checks"]["research"]= {"status":ready["research"]["status"], "sources_checked":ready["research"]["sources_checked"],
            "weather":[{"destination":d["name"],"confidence":d["weather"]["confidence"]} for d in ready["candidates"]]}
        post(endpoint,{"text":"Choose "+ready["candidates"][0]["name"]})
        built=post(endpoint,{"text":"Build itinerary"})
        edited=post(endpoint,{"text":"Day 2 is too busy. Make it relaxed."})
        assert edited["itinerary"]["days"][1]["pace"] == "relaxed"
        assert edited["itinerary"]["days"][0] == built["itinerary"]["days"][0]
        saved=post(endpoint,{"action":"save"})
        assert saved["plan_id"]
        report["checks"]["save_and_targeted_edit"] = True
        command("stop")
        session_model=TravelPlanningSession.objects.get(pk=session["id"])
        run=queue_research(session_model,recheck=True)
        assert run.status == "queued"
        connections.close_all()
        command("start")
        after=await_ready()
        assert after["research"]["id"] == run.id
        assert after["plan_id"] == saved["plan_id"]
        assert after["itinerary"]["days"][1]["pace"] == "relaxed"
        report["checks"]["queued_research_survives_restart"] = True
        report["checks"]["saved_context_survives_restart"] = True
        report["passed"]=True
    finally:
        try: command("stop")
        finally:
            output=report_path
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    main()
