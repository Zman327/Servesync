let modalEdited = false;

/**
 * Open the review modal and populate it with log data.
 * @param {Object} log - The log data to display.
 */
function openReviewModal(log) {
  modalEdited = false;
  document.getElementById('modal-student').innerText = `${log.student_name} (${log.user_id})`;
  document.getElementById('modal-activity').innerText = log.description;
  document.getElementById('modal-hours').innerText = log.hours;
  document.getElementById('modal-date').innerText = log.formatted_date;
  document.getElementById('modal-status').innerText = log.status_label;
  document.getElementById('modal-student-img').src = log.picture_url;
  document.getElementById('modal-group').innerText = log.group || "N/A";
  document.getElementById('modal-log-time').innerText = log.formatted_log_time;
  document.getElementById('approve-log-id').value = log.id;
  document.getElementById('reject-log-id').value = log.id;
  document.getElementById('edit-log-id').value = log.id;

  document.getElementById('reviewModal').style.display = 'block';
}

/**
 * Close the review modal and reload if edited.
 */
function closeModal() {
  document.getElementById('reviewModal').style.display = 'none';
  if (modalEdited) {
    window.location.reload();
  }
}

/**
 * Open the report modal.
 */
function openReportModal() {
  document.getElementById('reportModal').style.display = 'block';
}

/**
 * Close the report modal.
 */
function closeReportModal() {
  document.getElementById('reportModal').style.display = 'none';
}

/**
 * Open the approve tips modal.
 */
function openApproveTipsModal() {
  document.getElementById('approveTipsModal').style.display = 'block';
}

/**
 * Close the approve tips modal.
 */
function closeApproveTipsModal() {
  document.getElementById('approveTipsModal').style.display = 'none';
}

/**
 * Open the group tips modal.
 */
function openGroupTipsModal() {
  document.getElementById('groupTipsModal').style.display = 'block';
}

/**
 * Close the group tips modal.
 */
function closeGroupTipsModal() {
  document.getElementById('groupTipsModal').style.display = 'none';
}

/**
 * Open the manage group modal.
 */
function openManageGroupModal() {
  document.getElementById('manageGroupModal').style.display = 'block';
}

/**
 * Close the manage group modal.
 */
function closeManageGroupModal() {
  document.getElementById('manageGroupModal').style.display = 'none';
}

/**
 * Open the create group modal and close manage group modal.
 */
function openCreateGroupModal() {
  closeManageGroupModal();
  document.getElementById('createGroupModal').style.display = 'block';
}

/**
 * Close the create group modal and reopen manage group modal.
 */
function closeCreateGroupModal() {
  openManageGroupModal();
  document.getElementById('createGroupModal').style.display = 'none';
}

/**
 * Open the delete group modal with selected group info.
 */
function openDeleteGroupModal() {
  const groupSelect = document.getElementById('groupSelect');
  const selectedOption = groupSelect.options[groupSelect.selectedIndex];
  const groupId = selectedOption.value;
  const groupName = selectedOption.textContent;
  document.getElementById('deleteGroupId').value = groupId;
  document.getElementById('deleteGroupConfirmText').textContent = groupName;
  document.getElementById('deleteGroupModal').style.display = 'block';
}

/**
 * Close the delete group modal.
 */
function closeDeleteGroupModal() {
  document.getElementById('deleteGroupModal').style.display = 'none';
}

/**
 * Make an element editable and save edits on blur or Enter.
 * @param {string} id - The ID of the element to make editable.
 */
function makeEditable(id) {
  const el = document.getElementById(id);
  el.contentEditable = true;
  el.focus();
  el.classList.add("editing");

  function handleKey(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      el.blur();
    }
  }

  function handleBlur() {
    el.contentEditable = false;
    el.classList.remove("editing");
    el.removeEventListener("blur", handleBlur);
    el.removeEventListener("keydown", handleKey);
    saveEdits();
  }

  el.addEventListener("keydown", handleKey);
  el.addEventListener("blur", handleBlur);
}

/**
 * Save edits made in the modal by sending updated data to server.
 */
function saveEdits() {
  const logId = document.getElementById('edit-log-id').value;

  const rawDate = document.getElementById('modal-date').innerText.trim();
  const parsedDate = new Date(rawDate);
  const formattedDate = ("0" + parsedDate.getDate()).slice(-2) + "-" +
                        ("0" + (parsedDate.getMonth() + 1)).slice(-2) + "-" +
                        parsedDate.getFullYear();

  const data = {
    log_id: logId,
    description: document.getElementById('modal-activity').innerText.trim(),
    hours: document.getElementById('modal-hours').innerText.trim(),
    date: formattedDate
  };

  fetch('/update-log-field', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(result => {
    modalEdited = true;
  });
}

/**
 * Handle clicks outside modals to close them.
 */
window.onclick = function(event) {
  const reviewModal = document.getElementById('reviewModal');
  const reportModal = document.getElementById('reportModal');
  const approveTipsModal = document.getElementById('approveTipsModal');
  const groupTipsModal = document.getElementById('groupTipsModal');
  const manageGroupModal = document.getElementById('manageGroupModal');
  const createGroupModal = document.getElementById('createGroupModal');
  const deleteGroupModal = document.getElementById('deleteGroupModal');
  if (event.target === reviewModal) {
    reviewModal.style.display = "none";
  } else if (event.target === reportModal) {
    reportModal.style.display = "none";
  } else if (event.target === approveTipsModal) {
    approveTipsModal.style.display = "none";
  } else if (event.target === groupTipsModal) {
    groupTipsModal.style.display = "none";
  } else if (event.target === manageGroupModal) {
    manageGroupModal.style.display = "none";
  } else if (event.target === createGroupModal) {
    createGroupModal.style.display = "none";
  } else if (event.target === deleteGroupModal) {
    deleteGroupModal.style.display = "none";
  }
}

/**
 * Switch tabs and update active classes.
 * @param {string} tabName - The ID of the tab content to show.
 */
function openTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.getElementById(tabName).classList.add('active');
  event.currentTarget.classList.add('active');
}

/**
 * Populate group info fields based on selected option.
 * @param {HTMLSelectElement} select - The group select element.
 */
function populateGroupInfo(select) {
  const selectedOption = select.options[select.selectedIndex];
  const hours = selectedOption.getAttribute('data-hours');
  const name = selectedOption.textContent;

  document.getElementById('groupHours').value = hours;
  document.getElementById('groupName').value = name;
  const staff = selectedOption.getAttribute('data-staff');
  if (document.getElementById('manageStaffInCharge')) {
    document.getElementById('manageStaffInCharge').value = staff || "";
  }
}

/**
 * Print the staff submissions table in a new window.
 */
function printStaffTable() {
  const table = document.getElementById('submissionsTable').outerHTML;
  const printWindow = window.open('', '', 'height=800,width=1000');
  printWindow.document.write('<html><head><title>Service Hours Report</title>');
  printWindow.document.write('<style>');
  printWindow.document.write('table { width:100%; border-collapse: collapse; }');
  printWindow.document.write('table, th, td { border: 1px solid black; padding: 8px; }');
  printWindow.document.write('</style>');
  printWindow.document.write('</head><body>');
  printWindow.document.write('<h2>Service Hours Report</h2>');
  printWindow.document.write(table);
  printWindow.document.write('</body></html>');
  printWindow.document.close();
  printWindow.print();
}

// --- Pagination, Sorting and Search Logic ---
document.addEventListener('DOMContentLoaded', function () {
  const rows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
  const rowsPerPage = 10;
  let currentPage = 1;
  const totalPages = Math.ceil(rows.length / rowsPerPage);
  const pageIndicator = document.getElementById("pageIndicator");
  const prevBtn = document.getElementById("prevPage");
  const nextBtn = document.getElementById("nextPage");

  /**
   * Show a specific page of rows.
   * @param {number} page - The page number to show.
   */
  function showPage(page) {
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    rows.forEach((row, index) => {
      row.style.display = index >= start && index < end ? "" : "none";
    });
    if (pageIndicator) pageIndicator.textContent = `Page ${page}`;
    if (prevBtn) prevBtn.disabled = page === 1;
    if (nextBtn) nextBtn.disabled = page === totalPages || totalPages === 0;
  }

  if (prevBtn && nextBtn) {
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        showPage(currentPage);
      }
    });

    nextBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage++;
        showPage(currentPage);
      }
    });
  }

  // Default sort by Date (column 3) descending
  rows.sort((a, b) => {
    const cellA = a.cells[3].innerText;
    const cellB = b.cells[3].innerText;
    return new Date(cellB) - new Date(cellA);
  });
  rows.forEach(row => row.parentNode.appendChild(row));
  showPage(currentPage);

  // Sorting functionality
  let currentSortedColumn = null;
  let currentSortAsc = true;

  document.querySelectorAll(".sortable").forEach(header => {
    header.addEventListener("click", () => {
      const column = parseInt(header.getAttribute("data-column"));

      document.querySelectorAll(".sortable").forEach(h => h.classList.remove("asc", "desc"));
      document.querySelectorAll(".sort-icon").forEach(icon => icon.classList.remove("active"));

      if (currentSortedColumn === column) {
        currentSortAsc = !currentSortAsc;
      } else {
        currentSortAsc = true;
        currentSortedColumn = column;
      }

      header.classList.add(currentSortAsc ? "asc" : "desc");

      const icon = header.querySelector(".sort-icon");
      if (icon) icon.classList.add("active");

      rows.sort((a, b) => {
        const cellA = a.cells[column].innerText;
        const cellB = b.cells[column].innerText;

        if (column === 3) {
          return currentSortAsc
            ? new Date(cellA) - new Date(cellB)
            : new Date(cellB) - new Date(cellA);
        }

        const valA = cellA.toLowerCase();
        const valB = cellB.toLowerCase();

        if (!isNaN(valA) && !isNaN(valB)) {
          return currentSortAsc ? valA - valB : valB - valA;
        }

        return currentSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });

      rows.forEach(row => row.parentNode.appendChild(row));
      showPage(currentPage);
    });
  });

  // Search filter
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const searchTerm = searchInput.value.toLowerCase();

      rows.forEach(row => {
        const studentName = row.cells[0].textContent.toLowerCase();
        const date = row.cells[3].textContent.toLowerCase();
        const group = row.cells[5].textContent.toLowerCase();

        if (studentName.includes(searchTerm) || date.includes(searchTerm) || group.includes(searchTerm)) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // Row click to open review modal
  document.querySelectorAll('.submission-row').forEach(function(row) {
    row.addEventListener('click', function() {
      const studentName = this.getAttribute('data-student-name');
      const pictureUrl = this.getAttribute('data-picture-url');
      const userId = this.getAttribute('data-user-id');
      const description = this.getAttribute('data-description');
      const hours = this.getAttribute('data-hours');
      const date = this.getAttribute('data-date');
      const formattedDate = this.getAttribute('data-formatted-date');
      const statusLabel = this.getAttribute('data-status-label');
      const group = this.getAttribute('data-group');
      const formattedLogTime = this.getAttribute('data-formatted-log-time');
      const id = this.getAttribute('data-id');

      document.getElementById('modal-student').innerText = `${studentName} (${userId})`;
      document.getElementById('modal-activity').innerText = description;
      document.getElementById('modal-hours').innerText = hours;
      document.getElementById('modal-date').innerText = formattedDate || date;
      document.getElementById('modal-status').innerText = statusLabel;
      document.getElementById('modal-group').innerText = group || "N/A";
      document.getElementById('modal-log-time').innerText = formattedLogTime || "N/A";
      document.getElementById('approve-log-id').value = id;
      document.getElementById('reject-log-id').value = id;
      document.getElementById('edit-log-id').value = id;
      document.getElementById('modal-student-img').src = pictureUrl || '/static/default-profile.png';

      document.getElementById('reviewModal').style.display = 'block';
    });
  });
});

// --- Staff Autocomplete Logic ---
document.addEventListener('DOMContentLoaded', function() {
  var selectEl = document.getElementById('groupSelect');
  if (selectEl) {
    populateGroupInfo(selectEl);
  }

  const staffInputs = document.querySelectorAll('.staff-in-charge');

  /**
   * Attach autocomplete functionality to a staff input element.
   * @param {HTMLInputElement} inputEl - The input element to attach autocomplete.
   */
  function attachStaffAutocomplete(inputEl) {
    const box = inputEl.parentElement.querySelector('.staff-suggestions');
    let debounce;

    inputEl.addEventListener('input', () => {
      clearTimeout(debounce);
      const q = inputEl.value.trim().toLowerCase();
      if (!q) {
        if (box) box.innerHTML = '';
        return;
      }
      debounce = setTimeout(() => {
        fetch('/api/all-staff')
          .then(res => res.json())
          .then(list => {
            if (!box) return;
            box.innerHTML = '';
            list.forEach(staff => {
              const label = (staff.label || '').toLowerCase();
              if (label.includes(q)) {
                const li = document.createElement('li');
                li.textContent = staff.label;
                li.addEventListener('click', () => {
                  inputEl.value = staff.label;
                  inputEl.setAttribute('data-linked-staff-value', staff.value || staff.label);
                  inputEl.setAttribute('data-linked-staff-label', staff.label);
                  box.innerHTML = '';
                });
                box.appendChild(li);
              }
            });
          });
      }, 200);
    });

    inputEl.addEventListener('blur', () => {
      setTimeout(() => { if (box) box.innerHTML = ''; }, 150);
    });
  }

  staffInputs.forEach(attachStaffAutocomplete);

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.staff-in-charge') && !e.target.closest('.staff-suggestions')) {
      document.querySelectorAll('.staff-suggestions').forEach(ul => ul.innerHTML = '');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.staff-suggestions').forEach(ul => ul.innerHTML = '');
    }
  });
});