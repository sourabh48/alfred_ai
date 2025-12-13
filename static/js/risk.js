document.addEventListener("DOMContentLoaded", () => {
    loadRisk();
});

function loadRisk() {
    fetch("/api/risk/")
        .then(r => r.json())
        .then(data => {
            new Chart(document.getElementById("riskRadar"), {
                type: "radar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Risk Levels",
                        data: data.values,
                        borderColor: "#e17055",
                        backgroundColor: "rgba(225,112,85,0.2)",
                        borderWidth: 3
                    }]
                },
                options: {
                    scales: { r: { min: 0, max: 100 } }
                }
            });
        });
}
