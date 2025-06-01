function simplifyTask() {
  const task = document.getElementById("taskInput").value;

  fetch("/simplify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task })
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("output").innerText = data.simplified || "No response.";
  })
  .catch(err => {
    document.getElementById("output").innerText = "Error: " + err.message;
  });
}
