document.getElementById('codeForm').addEventListener('submit', function (e) {
  e.preventDefault();

  const code = document.getElementById('code').value.trim();

  if (!code) {
    alert("Please enter some code to explain.");
    return;
  }

  fetch('/explain_code', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ code: code })
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      alert(data.error);
      return;
    }

    const explanationContainer = document.getElementById('explanationContainer');
    const explanationText = document.getElementById('explanationText');

    explanationText.textContent = data.explanation;
    explanationContainer.style.display = 'block';
  })
  .catch(error => {
    console.error('Error:', error);
    alert("An error occurred while explaining the code.");
  });
});

// Auto-resize textarea
function resizeTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";

  const lines = textarea.value.split('\n');
  const longestLine = lines.reduce((a, b) => a.length > b.length ? a : b, '');
  
  const tempSpan = document.createElement("span");
  tempSpan.style.visibility = "hidden";
  tempSpan.style.position = "absolute";
  tempSpan.style.whiteSpace = "pre";
  tempSpan.style.font = window.getComputedStyle(textarea).font;
  tempSpan.textContent = longestLine || ' ';
  document.body.appendChild(tempSpan);
  
  textarea.style.width = (tempSpan.offsetWidth + 30) + "px";
  document.body.removeChild(tempSpan);
}


// Call once on load for smooth UX
document.addEventListener('DOMContentLoaded', function () {
  const textarea = document.getElementById('code');
  resizeTextarea(textarea);
  textarea.addEventListener('input', () => resizeTextarea(textarea));
});
