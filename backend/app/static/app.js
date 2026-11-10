const status = document.querySelector("#status");
const retry = document.querySelector("#retry");

async function checkConnection() {
  retry.hidden = true;
  status.textContent = "Connecting...";
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("API request failed");
    const result = await response.json();
    status.textContent = result.message;
  } catch {
    status.textContent = "Unable to connect. Please try again.";
    retry.hidden = false;
  }
}

retry.addEventListener("click", checkConnection);
checkConnection();
