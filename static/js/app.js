// Global Dashboard Chart Loader
if (document.getElementById("expenseChart")) {

    fetch("/api/expenses/chart/")
        .then(res => res.json())
        .then(data => {
            new Chart(document.getElementById("expenseChart"), {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Expenses",
                        data: data.values,
                        borderColor: "#007bff",
                        borderWidth: 2
                    }]
                }
            });
        });
}
