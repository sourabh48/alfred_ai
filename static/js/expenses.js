document.addEventListener("DOMContentLoaded", () => {
    loadCards();
    loadTrend();
});

// Load animated cards
function loadCards() {
    fetch("/api/expenses/")
        .then(r => r.json())
        .then(data => {
            let container = document.getElementById("expenseCards");
            container.innerHTML = "";

            data.forEach(exp => {
                const categoryColors = {
                    Food: "#ff7979",
                    Travel: "#badc58",
                    Bills: "#7ed6df",
                    Shopping: "#f9ca24",
                    Other: "#e056fd"
                };

                let color = categoryColors[exp.category] || "#6c5ce7";

                container.innerHTML += `
                    <div class="col-lg-4">
                        <div class="glass-card p-3 fade-in">
                            <div class="d-flex justify-content-between">
                                <span class="badge-category" style="background:${color}">${exp.category}</span>
                                <small>${exp.date}</small>
                            </div>

                            <h3 class="mt-2 mb-2 text-dark">₹${exp.amount}</h3>
                            <p class="text-muted">${exp.notes || ""}</p>

                            <button class="btn btn-danger btn-sm" onclick="deleteExpense(${exp.id})">Delete</button>
                        </div>
                    </div>
                `;
            });
        });
}

// Delete
function deleteExpense(id) {
    fetch(`/api/expenses/${id}/`, { method: "DELETE" })
        .then(() => loadCards());
}

// Add Expense
document.getElementById("addExpenseForm")
    .addEventListener("submit", function(e){
        e.preventDefault();

        const data = Object.fromEntries(new FormData(this));

        fetch("/api/expenses/", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        }).then(() => {
            loadCards();
            document.querySelector("#addModal .btn-close").click();
        });
    });

// Chart
function loadTrend() {
    fetch("/api/expenses/chart/")
        .then(r => r.json())
        .then(d => {
            new Chart(document.getElementById("expenseTrend"), {
                type: 'line',
                data: {
                    labels: d.labels,
                    datasets: [{
                        label: "Monthly Expenses",
                        data: d.values,
                        borderColor: "#0066ff",
                        tension: 0.3,
                        fill: true,
                        backgroundColor: "rgba(0,102,255,0.08)"
                    }]
                }
            });
        });
}
