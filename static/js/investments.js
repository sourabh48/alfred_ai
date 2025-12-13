document.addEventListener("DOMContentLoaded", () => {
    loadPortfolio();
    loadCharts();
});

function loadPortfolio() {
    fetch("/api/investments/")
        .then(r => r.json())
        .then(data => {
            document.getElementById("totalValue").innerHTML = "₹" + data.total_value;
            document.getElementById("annualReturn").innerHTML = data.return_rate + "%";
            document.getElementById("riskRating").innerHTML = data.risk;
        });
}

function loadCharts() {
    fetch("/api/investments/allocation/")
        .then(r => r.json())
        .then(data => {
            new Chart(document.getElementById("allocationChart"), {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.values,
                        backgroundColor: ["#6c5ce7", "#00cec9", "#fdcb6e", "#e17055", "#0984e3"]
                    }]
                }
            });
        });

    fetch("/api/investments/growth/")
        .then(r => r.json())
        .then(data => {
            new Chart(document.getElementById("growthChart"), {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Portfolio Value",
                        data: data.values,
                        borderColor: "#0984e3",
                        tension: 0.4,
                        fill: true,
                        backgroundColor: "rgba(9,132,227,0.1)"
                    }]
                }
            });
        });
}
