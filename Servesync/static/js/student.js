document.addEventListener("DOMContentLoaded", () => {
  function showGroupError(show) {
    const errorBox = document.getElementById("group-error");
    const helperText = document.getElementById("group-helper-text");
    if (show) {
      const groupInput = document.getElementById("group");
      const container = groupInput.closest(".form-group");
      if (container && errorBox.parentNode !== container.parentNode) {
        container.parentNode.insertBefore(errorBox, container.nextSibling);
      }
      errorBox.style.display = "block";
      helperText.style.display = "none";
    } else {
      errorBox.style.display = "none";
      helperText.style.display = "block";
    }
  }

  function showStaffError(show) {
    const errorBox = document.getElementById("staff-error");
    const helperText = document.getElementById("staff-helper-text");
    if (show) {
      const staffInput = document.getElementById("person_in_charge");
      const container = staffInput.closest(".form-group");
      if (container && errorBox.parentNode !== container.parentNode) {
        container.parentNode.insertBefore(errorBox, container.nextSibling);
      }
      errorBox.style.display = "block";
      helperText.style.display = "none";
    } else {
      errorBox.style.display = "none";
      helperText.style.display = "block";
    }
  }

  const dateInput = document.getElementById("date");
  if (dateInput) {
    const today = new Date();
    const localDate = today.toLocaleDateString('en-CA'); // formats as YYYY-MM-DD
    dateInput.setAttribute("max", localDate);
    dateInput.value = localDate;
    const currentYear = today.getFullYear();
    const minDate = `${currentYear}-01-01`;
    dateInput.setAttribute("min", minDate);
  }

  // Confirmation message animation with auto-dismiss
  const confirmation = document.getElementById("confirmation-message");
  if (confirmation) {
    confirmation.classList.add("show");
    confirmation.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => {
      confirmation.style.opacity = "0";
      setTimeout(() => confirmation.remove(), 500);
    }, 5000);
  }

  // Form validation and submit animation
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", (e) => {
      const formErrorMessage = document.getElementById("form-error-message");
      if (formErrorMessage) {
        formErrorMessage.style.display = "none";
      }
      let hasError = false;
      form.querySelectorAll("input[required]").forEach((input) => {
        if (!input.value.trim()) {
          input.classList.add("input-error");
          const icon = input.parentElement.querySelector('i');
          const label = input.parentElement.querySelector('label');
          if (icon) {
            icon.classList.add("input-error-icon");
            setTimeout(() => icon.classList.remove("input-error-icon"), 600);
          }
          if (label) {
            label.classList.add("label-error");
            setTimeout(() => label.classList.remove("label-error"), 600);
          }
          hasError = true;
          setTimeout(() => input.classList.remove("input-error"), 600);
        }
      });

      const hoursInput = document.getElementById("hours");
      if (hoursInput) {
        const hours = parseFloat(hoursInput.value);
        if (hours <= 0) {
          hoursInput.classList.add("input-error");
          const hoursIcon = hoursInput.parentElement.querySelector('i');
          const hoursLabel = hoursInput.parentElement.querySelector('label');
          if (hoursIcon) {
            hoursIcon.classList.add("input-error-icon");
            setTimeout(() => hoursIcon.classList.remove("input-error-icon"), 600);
          }
          if (hoursLabel) {
            hoursLabel.classList.add("label-error");
            setTimeout(() => hoursLabel.classList.remove("label-error"), 600);
          }
          alert("Hours must be greater than 0.");
          e.preventDefault();
          return;
        }
      }

      if (hasError) {
        const errorMessage = document.getElementById("form-error-message");
        if (errorMessage) {
          errorMessage.style.display = "block";
          errorMessage.classList.remove("fade-out"); // reset if already fading

          setTimeout(() => {
            errorMessage.classList.add("fade-out");
            setTimeout(() => {
              errorMessage.style.display = "none";
              errorMessage.classList.remove("fade-out");
            }, 500); // match the CSS transition duration
          }, 2000); // visible for 2 seconds
        }
        e.preventDefault();
        return;
      }

      const btnText = form.querySelector(".btn-text");
      const btnLoader = form.querySelector(".btn-loader");
      if (btnText && btnLoader) {
        btnText.style.display = "none";
        btnLoader.style.display = "inline-block";
      }
    });
  }

  const groupInput = document.getElementById("group");
  const suggestionBox = document.getElementById("group-suggestions");

  if (groupInput) {
    let timeout;
    groupInput.addEventListener("input", () => {
      clearTimeout(timeout);
      const query = groupInput.value.trim();
      if (!query) {
        if (suggestionBox) {
          suggestionBox.innerHTML = "";
        }
        return;
      }
      timeout = setTimeout(() => {
        fetch(`/api/groups?q=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(groups => {
            if (suggestionBox) {
              suggestionBox.innerHTML = "";
              groups.forEach(group => {
                const li = document.createElement("li");
                li.textContent = group;
                li.addEventListener("click", () => {
                  groupInput.value = group;
                  showGroupError(false);

                  // Clear error state if selecting from dropdown
                  const errorBox = document.getElementById("group-error");
                  const icon = groupInput.parentElement.querySelector("i");
                  if (errorBox) errorBox.style.display = "none";
                  groupInput.classList.remove("input-error");
                  if (icon) icon.classList.remove("input-error-icon");

                  if (suggestionBox) {
                    suggestionBox.innerHTML = "";
                  }

                  // Fetch and populate the staff member linked to this group
                  fetch(`/api/staff-for-group?group=${encodeURIComponent(group)}`)
                    .then(res => res.json())
                    .then(staff => {
                      const personSelect = document.getElementById("person_in_charge");
                      if (staff && staff.label && personSelect) {
                        personSelect.value = staff.label;
                        personSelect.setAttribute("data-linked-staff-value", staff.value);
                        personSelect.setAttribute("data-linked-staff-label", staff.label);
                      }
                    });
                });
                suggestionBox.appendChild(li);
              });
            }
          });
      }, 200);
    });

    groupInput.addEventListener("blur", () => {
      setTimeout(() => {
        const query = groupInput.value.trim();
        const errorBox = document.getElementById("group-error");
        const icon = groupInput.parentElement.querySelector("i");

        if (!query) {
          groupInput.value = "Other";
          showGroupError(false);
          groupInput.classList.remove("input-error");
          if (icon) icon.classList.remove("input-error-icon");

          // Fetch and auto-fill staff linked to "Other"
          fetch(`/api/staff-for-group?group=Other`)
            .then(res => res.json())
            .then(staff => {
              const personSelect = document.getElementById("person_in_charge");
              if (staff && staff.label && personSelect) {
                personSelect.value = staff.label;
                personSelect.setAttribute("data-linked-staff-value", staff.value);
                personSelect.setAttribute("data-linked-staff-label", staff.label);
              }
            });

          return;
        }

        fetch(`/api/groups?q=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(groups => {
            const match = groups.some(group => group.toLowerCase() === query.toLowerCase());
            if (!match) {
              showGroupError(true);
              groupInput.classList.add("input-error");
              if (icon) icon.classList.add("input-error-icon");

              // Re-trigger animation
              groupInput.classList.remove("input-error");
              void groupInput.offsetWidth;
              groupInput.classList.add("input-error");

              if (icon) {
                icon.classList.remove("input-error-icon");
                void icon.offsetWidth;
                icon.classList.add("input-error-icon");
              }
            } else {
              showGroupError(false);
              groupInput.classList.remove("input-error");
              if (icon) icon.classList.remove("input-error-icon");
            }
          });
      }, 200); // Delay by 200ms
    });
  }

  document.addEventListener("click", (e) => {
    if (groupInput && suggestionBox && !e.target.closest(".autocomplete-group")) {
      suggestionBox.innerHTML = "";
    }
  });

  const staffInput = document.getElementById("person_in_charge");

  if (staffInput) {
    // Autofill group input when clicking on a group in the table
    const groupCells = document.querySelectorAll(".group-clickable");
    groupCells.forEach(cell => {
      cell.addEventListener("click", () => {
        const groupName = cell.getAttribute("data-group");
        if (groupInput) {
          groupInput.value = groupName;

          // Optional: trigger input event to refresh suggestions
          groupInput.dispatchEvent(new Event("input"));

          // Optionally hide any error message
          showGroupError(false);
        }

        // Fetch and populate the staff member linked to this group
        fetch(`/api/staff-for-group?group=${encodeURIComponent(groupName)}`)
          .then(res => res.json())
          .then(staff => {
            if (staff && staff.label) {
              staffInput.value = staff.label;
              staffInput.setAttribute("data-linked-staff-value", staff.value);
              staffInput.setAttribute("data-linked-staff-label", staff.label);
            }
          });
      });
    });

    const staffBox = document.getElementById("staff-suggestions");

    let staffTimeout;
    staffInput.addEventListener("input", () => {
      clearTimeout(staffTimeout);
      const query = staffInput.value.trim().toLowerCase();
      if (!query) {
        if (staffBox) {
          staffBox.innerHTML = "";
        }
        return;
      }
      staffTimeout = setTimeout(() => {
        fetch(`/api/all-staff`)
          .then(res => res.json())
          .then(staffList => {
            if (staffBox) {
              staffBox.innerHTML = "";
              staffList.forEach(staff => {
                if (staff.label.toLowerCase().includes(query)) {
                  const li = document.createElement("li");
                  li.textContent = staff.label;
                  li.addEventListener("click", () => {
                    staffInput.value = staff.label;
                    if (staffBox) {
                      staffBox.innerHTML = "";
                    }
                  });
                  staffBox.appendChild(li);
                }
              });
            }
          });
      }, 200);
    });

    document.addEventListener("click", (e) => {
      if (staffBox && !e.target.closest("#person_in_charge")) {
        staffBox.innerHTML = "";
      }
    });

    staffInput.addEventListener("blur", () => {
      setTimeout(() => {
        const query = staffInput.value.trim().toLowerCase();
        const icon = staffInput.parentElement.querySelector("i");

        if (!query) {
          showStaffError(false);
          staffInput.classList.remove("input-error");
          if (icon) icon.classList.remove("input-error-icon");
          return;
        }

        fetch(`/api/all-staff`)
          .then(res => res.json())
          .then(staffList => {
            const match = staffList.some(staff =>
              staff.label.toLowerCase() === query
            );
            if (!match) {
              showStaffError(true);
              staffInput.classList.add("input-error");
              if (icon) icon.classList.add("input-error-icon");

              staffInput.classList.remove("input-error");
              void staffInput.offsetWidth;
              staffInput.classList.add("input-error");

              if (icon) {
                icon.classList.remove("input-error-icon");
                void icon.offsetWidth;
                icon.classList.add("input-error-icon");
              }
            } else {
              showStaffError(false);
              staffInput.classList.remove("input-error");
              if (icon) icon.classList.remove("input-error-icon");
            }
          });
      }, 200);
    });
  }

  // Render pie chart for progress bar
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  if (progressBar && progressText) {
    const userHours = parseFloat(progressBar.getAttribute("data-hours")) || 0;
    const nextAwardThreshold = parseFloat(progressBar.getAttribute("data-goal")) || 20;
    const maxAwardThreshold = parseFloat(progressBar.getAttribute("data-max-award-threshold")) || nextAwardThreshold;
    const goal = userHours >= maxAwardThreshold ? maxAwardThreshold : nextAwardThreshold;
    const percentage = Math.min((userHours / goal) * 100, 100);

    console.log("DEBUG: userHours =", userHours);
    console.log("DEBUG: nextAwardThreshold =", nextAwardThreshold);
    console.log("DEBUG: maxAwardThreshold =", maxAwardThreshold);
    console.log("DEBUG: goal =", goal);
    console.log("DEBUG: percentage =", percentage);

    progressBar.style.background = `conic-gradient(var(--jungle-green) ${percentage}%, #e0e0e0 ${percentage}%)`;
    progressText.innerText = `${userHours} / ${goal}`;
  }
});