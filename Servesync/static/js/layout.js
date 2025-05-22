function openLoginModal() {
  document.getElementById("loginModal").style.display = "flex";
}

function closeLoginModal() {
  document.getElementById("loginModal").style.display = "none";
}

window.onclick = function(event) {
  const modal = document.getElementById("loginModal");
  if (event.target === modal) {
    closeLoginModal();
  }
};

// Close modal on Escape key
window.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    closeLoginModal();
  }
});

// Toggle password visibility
function togglePasswordVisibility() {
  const pwField = document.getElementById("password");
  const toggle = document.getElementById("togglePassword");
  const lockIcon = document.getElementById("lockIcon");

  if (pwField.type === "password") {
    pwField.type = "text";
    toggle.classList.remove("bxs-eye");
    toggle.classList.add("bxs-hide");

    lockIcon.classList.remove("bxs-lock-alt");
    lockIcon.classList.add("bxs-lock-open-alt");
  } else {
    pwField.type = "password";
    toggle.classList.remove("bxs-hide");
    toggle.classList.add("bxs-eye");

    lockIcon.classList.remove("bxs-lock-open-alt");
    lockIcon.classList.add("bxs-lock-alt");
  }
}

let dropdownTimeout;

const dropdown = document.querySelector(".dropdown");

if (dropdown) {
  dropdown.addEventListener("mouseenter", () => {
    clearTimeout(dropdownTimeout);
    const content = dropdown.querySelector(".dropdown-content");
    if (content) content.style.display = "block";
  });

  dropdown.addEventListener("mouseleave", () => {
    dropdownTimeout = setTimeout(() => {
      const content = dropdown.querySelector(".dropdown-content");
      if (content) content.style.display = "none";
    }, 100); // Delay in milliseconds
  });
}

window.onload = function () {
  const flashMessages = document.querySelector(".flash-messages");
  if (flashMessages) {
    openLoginModal();
    setTimeout(() => {
      document.querySelectorAll('input.error').forEach(input => {
        input.classList.remove('error');
      });
    }, 1000);
  }
};
