const chatBox = document.getElementById('chat-box');
const inputForm = document.getElementById('input-form');
const inputMessage = document.getElementById('input-message');

function appendMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.classList.add('message', sender);

  let formattedText = text
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\n/g, "<br>");

  msgDiv.innerHTML = formattedText;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

inputForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = inputMessage.value.trim();
  if (!message) return;

  appendMessage("You: " + message, 'user');
  inputMessage.value = '';

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({message})
    });

    const data = await response.json();
    appendMessage("NeuroBuddy: " + data.reply, 'bot');
  } catch (err) {
    appendMessage("Error contacting server.", 'bot');
  }
});
