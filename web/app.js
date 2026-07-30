const watchlistData = [
  { symbol: "AAPL", name: "Apple", price: "224.31", change: "+1.28%", logo: "A" },
  { symbol: "NVDA", name: "NVIDIA", price: "117.93", change: "+3.42%", logo: "N" },
  { symbol: "MSFT", name: "Microsoft", price: "418.79", change: "+1.18%", logo: "M" },
  { symbol: "TSLA", name: "Tesla", price: "220.25", change: "-1.26%", logo: "T" },
  { symbol: "AMZN", name: "Amazon", price: "186.41", change: "+0.62%", logo: "A" },
];

const watchlist = document.querySelector("#watchlist");
watchlist.innerHTML = watchlistData.map((item) => `
  <div class="watch-row">
    <div class="security">
      <span class="security-logo">${item.logo}</span>
      <div><strong>${item.symbol}</strong><small>${item.name}</small></div>
    </div>
    <strong>${item.price}</strong>
    <span class="${item.change.startsWith("-") ? "negative" : ""}">${item.change}</span>
  </div>
`).join("");

const aiRail = document.querySelector("#aiRail");
document.querySelector("#aiToggle").addEventListener("click", () => aiRail.classList.add("open"));
document.querySelector("#aiClose").addEventListener("click", () => aiRail.classList.remove("open"));

const modal = document.querySelector("#commandModal");
const commandInput = document.querySelector("#commandInput");
function openCommand() {
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => commandInput.focus(), 100);
}
function closeCommand() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}
document.querySelector("#commandTrigger").addEventListener("click", openCommand);
modal.addEventListener("click", (event) => { if (event.target === modal) closeCommand(); });
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openCommand();
  }
  if (event.key === "Escape") {
    closeCommand();
    aiRail.classList.remove("open");
  }
});

document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item[data-view]").forEach((nav) => nav.classList.remove("active"));
    item.classList.add("active");
    document.querySelector(".eyebrow").textContent = `${item.dataset.view.toUpperCase()} WORKSPACE`;
  });
});

document.querySelectorAll(".timeframes button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".timeframes button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  });
});

function updateClock() {
  const value = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
  document.querySelector("#clock").textContent = value;
}
updateClock();
setInterval(updateClock, 1000);
