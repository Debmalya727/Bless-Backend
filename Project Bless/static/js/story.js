async function generateStory() {
    const genre = document.getElementById("genre").value;
    const character = document.getElementById("character").value;
    const storyIdea = document.getElementById("storyIdea").value; // New field

    const response = await fetch("/story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ genre, character, storyIdea }) // Include in request
    });

    const data = await response.json();
    const output = document.getElementById("story-output");

    if (data.story) {
        output.innerText = data.story;
    } else if (data.error) {
        output.innerText = "Error: " + data.error;
    } else {
        output.innerText = "Unexpected response.";
    }

    output.scrollTop = 0; // Scroll to top
}

async function claimReward() {
        const wallet = document.getElementById('wallet').value;

        if (!wallet || !wallet.startsWith("0x") || wallet.length !== 42) {
            alert("Please enter a valid Ethereum wallet address.");
            return;
        }

        try {
            const response = await fetch('/reward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ wallet: wallet, amount: 10 })  // default reward
            });

            const data = await response.json();
            if (response.ok) {
                alert("Reward sent! Transaction Hash: " + data.tx_hash);
            } else {
                alert("Error: " + data.error);
            }
        } catch (error) {
            alert("Request failed: " + error.message);
        }
    }