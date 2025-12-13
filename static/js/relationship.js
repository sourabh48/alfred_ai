document.addEventListener("DOMContentLoaded", () => {
    loadCompatibility();
});

function loadCompatibility() {
    fetch("/api/relationship/alignment/")
        .then(r => r.json())
        .then(d => {
            new Chart(document.getElementById("relationshipRadar"), {
                type: "radar",
                data: {
                    labels: d.labels,
                    datasets: [
                        {
                            label: "You",
                            data: d.you,
                            borderColor: "#6c5ce7",
                            backgroundColor: "rgba(108,92,231,0.2)"
                        },
                        {
                            label: "Partner",
                            data: d.partner,
                            borderColor: "#00cec9",
                            backgroundColor: "rgba(0,206,201,0.2)"
                        }
                    ]
                }
            });
        });
}
