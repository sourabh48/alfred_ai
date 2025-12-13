document.addEventListener("DOMContentLoaded", () => {
    loadSalaryProjection();
});

function loadSalaryProjection() {
    fetch("/api/career/projection/")
        .then(r => r.json())
        .then(data => {
            new Chart(document.getElementById("salaryChart"), {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Salary Projection",
                        data: data.values,
                        borderColor: "#00b894",
                        fill: true,
                        tension: 0.35,
                        backgroundColor: "rgba(0,184,148,0.2)"
                    }]
                }
            });
        });
}
