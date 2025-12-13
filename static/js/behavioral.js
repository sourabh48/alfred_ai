document.addEventListener("DOMContentLoaded", () => {
    loadStress();
    loadBehaviorFingerprint();
});

function loadStress() {
    fetch("/api/behavioral/stress/")
        .then(r => r.json())
        .then(d => {
            new Chart(document.getElementById("stressChart"), {
                type: "line",
                data: { labels: d.labels,
                    datasets: [{
                        label: "Stress Level",
                        data: d.values,
                        borderColor: "#e74c3c",
                        fill: true,
                        backgroundColor: "rgba(231,76,60,0.2)"
                    }]
                }
            });
        });
}

function loadBehaviorFingerprint() {
    fetch("/api/behavioral/fingerprint/")
        .then(r => r.json())
        .then(d => {
            new Chart(document.getElementById("behaviorChart"), {
                type: "radar",
                data: {
                    labels: d.labels,
                    datasets: [{
                        label: "Behavior Profile",
                        data: d.values,
                        backgroundColor: "rgba(108,92,231,0.2)",
                        borderColor: "#6c5ce7",
                        borderWidth: 2
                    }]
                }
            });
        });
}
