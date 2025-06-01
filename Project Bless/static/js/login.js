async function loginWithWallet() {
            if (!window.ethereum) {
                document.getElementById("status").innerText = "Install MetaMask to continue.";
                return;
            }

            try {
                const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
                const wallet = accounts[0];

                const message = `Login to NeuroBuddy with wallet: ${wallet}`;
                const signature = await ethereum.request({
                    method: 'personal_sign',
                    params: [message, wallet],
                });

                const res = await fetch("/check_wallet", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ wallet })
                });

                const data = await res.json();
                if (data.exists) {
                    localStorage.setItem("wallet", wallet);
                    window.location.href = "/home"; // Go to index.html
                } else {
                    document.getElementById("status").innerText = "Wallet not registered. Please sign up first.";
                }
            } catch (err) {
                console.error(err);
                document.getElementById("status").innerText = "Login failed. Please try again.";
            }
        }

        async function startSignup() {
            if (!window.ethereum) {
                document.getElementById("status").innerText = "Install MetaMask to continue.";
                return;
            }

            try {
                const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
                const wallet = accounts[0];

                const message = `Sign up for NeuroBuddy with wallet: ${wallet}`;
                const signature = await ethereum.request({
                    method: 'personal_sign',
                    params: [message, wallet],
                });

                await fetch("/signup", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ wallet })
                });

                localStorage.setItem("wallet", wallet);
                window.location.href = "/home"; // Redirect after signup
            } catch (err) {
                console.error(err);
                document.getElementById("status").innerText = "Signup failed. Please try again.";
            }
        }