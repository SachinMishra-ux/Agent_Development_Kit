/**
 * Sample Frontend JavaScript with intentional UI bugs & security vulnerabilities.
 */

// Bug 1: Storing sensitive token in plain localStorage (XSS theft risk)
function saveSession(token) {
    localStorage.setItem("authToken", token);
}

// Bug 2: DOM XSS vulnerability via innerHTML
function displayUserProfile(userData) {
    const profileContainer = document.getElementById("profile");
    // Insecure: directly injecting user-controlled HTML string
    profileContainer.innerHTML = "<h3>User: " + userData.name + "</h3><p>" + userData.bio + "</p>";
}

// Bug 3: Unhandled fetch network rejection
function submitFormData(payload) {
    fetch("/api/register", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" }
    }).then(res => res.json());
    // Missing .catch() or error handler
}
