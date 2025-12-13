document.addEventListener("DOMContentLoaded", () => {
    loadFamilyGrowth();
});

function loadFamilyGrowth() {
    fetch("/api/family/growth/")
        .then(r => r.json())
        .then(data => {
            new Chart(document.getElementById("familyNetChart"), {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Net Worth",
                        data: data.values,
                        backgroundColor: "#6c5ce7"
                    }]
                }
            });
        });
}
