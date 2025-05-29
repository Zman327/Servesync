// General-purpose table sorting function
function sortTableByColumn(tableId, columnIndex, ascending = true) {
    const table = document.getElementById(tableId);
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.querySelectorAll("tr"));
  
    const sortedRows = rows.sort((a, b) => {
      const aText = a.children[columnIndex].textContent.trim().toLowerCase();
      const bText = b.children[columnIndex].textContent.trim().toLowerCase();
  
      const aVal = parseFloat(aText);
      const bVal = parseFloat(bText);
  
      if (!isNaN(aVal) && !isNaN(bVal)) {
        return ascending ? aVal - bVal : bVal - aVal;
      }
      return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
  
    sortedRows.forEach(row => tbody.appendChild(row));
  }
  
  document.querySelectorAll('.sidebar ul li a').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = link.getAttribute('data-target');
      document.querySelectorAll('.content-section').forEach(sec => sec.style.display = 'none');
      document.getElementById(`content-${target}`).style.display = 'block';
      document.querySelector('.sidebar ul li a.active')?.classList.remove('active');
      link.classList.add('active');
    });
  });
  
  // Register ChartDataLabels plugin
  Chart.register(ChartDataLabels);
  
  // Student Growth Over Time
  new Chart(document.getElementById('chart-students-over-time'), {
    type: 'line',
    data: {
      labels: chartLabels,
      datasets: [{ 
        label: 'New Submissions',
        data: chartData,
        fill: false,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Students Over Time',
          font: {
            size: 18
          }
        }
      }
    }
  });
  
// Submission Status Overview (Bar Chart)
new Chart(document.getElementById('chart-hours-by-group'), {
    type: 'bar',
    data: {
      labels: ['Approved', 'Pending', 'Rejected'],
      datasets: [{
        label: 'Number of Submissions',
        data: [120, 30, 10], 
        backgroundColor: [
          '#4CAF50',  // Approved - green
          '#FFC107',  // Pending - amber
          '#F44336'   // Rejected - red
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Submission Status Overview',
          font: {
            size: 18
          }
        },
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Submission Count'
          }
        }
      }
    }
  });
  
  // Award Distribution Chart (Pie)
  new Chart(document.getElementById('chart-award-distribution'), {
    type: 'pie',
    data: {
      labels: awardLabels,
      datasets: [{
        data: awardCounts,
        backgroundColor: awardColors
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Award Distribution',
          font: {
            size: 18
          }
        },
        datalabels: {
          color: '#fff',
          font: {
            weight: 'bold',
            size: 14
          },
          formatter: (value, context) => {
            const data = context.chart.data.datasets[0].data;
            const total = data.reduce((acc, val) => acc + val, 0);
            const percentage = (value / total) * 100;
            return percentage >= 1 ? `${percentage.toFixed(1)}%` : '';
          }
        }
      }
    },
    plugins: [ChartDataLabels]
  });
  
  document.addEventListener("DOMContentLoaded", function () {
    const rows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
    const rowsPerPage = 7;
    let currentPage = 1;
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    const pageIndicator = document.getElementById("pageIndicator");
    const prevBtn = document.getElementById("prevPage");
    const nextBtn = document.getElementById("nextPage");
  
    function showPage(page) {
      const start = (page - 1) * rowsPerPage;
      const end = start + rowsPerPage;
      rows.forEach((row, index) => {
        row.style.display = index >= start && index < end ? "" : "none";
      });
      pageIndicator.textContent = `Page ${page}`;
      prevBtn.disabled = page === 1;
      nextBtn.disabled = page === totalPages || totalPages === 0;
    }
  
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
  
    rows.sort((a, b) => {
      const cellA = a.cells[3].innerText;
      const cellB = b.cells[3].innerText;
      return new Date(cellB) - new Date(cellA);
    });
    rows.forEach(row => row.parentNode.appendChild(row));
    showPage(currentPage);
  
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
  });
  
  document.addEventListener("DOMContentLoaded", function () {
    const allRows = Array.from(document.querySelectorAll("#submissionsTable tbody tr"));
    const rowsPerPage = 7;
    let currentPage = 1;
    let filteredRows = [...allRows];
  
    const pageIndicator = document.getElementById("pageIndicator");
    const prevBtn = document.getElementById("prevPage");
    const nextBtn = document.getElementById("nextPage");
    const searchInput = document.getElementById("searchInput");
  
    function showPage(page) {
      const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
      const start = (page - 1) * rowsPerPage;
      const end = start + rowsPerPage;
  
      allRows.forEach(row => row.style.display = "none");
      filteredRows.slice(start, end).forEach(row => row.style.display = "");
  
      pageIndicator.textContent = `Page ${page}`;
      prevBtn.disabled = page === 1;
      nextBtn.disabled = page === totalPages || totalPages === 0;
    }
  
    function updateSearchAndPagination() {
      const searchTerm = searchInput.value.toLowerCase();
  
      filteredRows = allRows.filter(row => {
        const studentName = row.cells[0].textContent.toLowerCase();
        const date = row.cells[3].textContent.toLowerCase();
        const group = row.cells[5].textContent.toLowerCase();
        return studentName.includes(searchTerm) || date.includes(searchTerm) || group.includes(searchTerm);
      });
  
      currentPage = 1;
      showPage(currentPage);
    }
  
    searchInput.addEventListener("input", updateSearchAndPagination);
  
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        showPage(currentPage);
      }
    });
  
    nextBtn.addEventListener("click", () => {
      const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
      if (currentPage < totalPages) {
        currentPage++;
        showPage(currentPage);
      }
    });
  
    updateSearchAndPagination();
  });
  
  // Review Modal and Student Info Modal Handlers
  document.addEventListener("DOMContentLoaded", function () {
    // Review Modal Handler
    document.querySelectorAll(".review-btn").forEach(button => {
      button.addEventListener("click", function () {
        const row = this.closest(".submission-row");
  
        // Open Review Modal with submission data
        openReviewModal({
          pictureUrl: row.dataset.pictureUrl,
          studentName: row.dataset.studentName,
          group: row.dataset.group,
          description: row.dataset.description,
          hours: row.dataset.hours,
          date: row.dataset.date,
          status: row.dataset.statusLabel,
          formattedLogTime: row.dataset.formattedLogTime,
          submissionId: row.dataset.id
        });
      });
    });
  
    // Function to open the Review Modal and populate fields
    function openReviewModal(data) {
      document.getElementById("modal-student-img").src = data.pictureUrl || '/static/default-profile.png';
      document.getElementById("modal-student").textContent = data.studentName;
      document.getElementById("modal-group").textContent = data.group;
      document.getElementById("modal-activity").textContent = data.description;
      document.getElementById("modal-hours").textContent = data.hours;
      document.getElementById("modal-date").textContent = data.date;
      document.getElementById("modal-status").textContent = data.status;
      document.getElementById("modal-log-time").textContent = data.formattedLogTime;
      document.getElementById("approve-log-id").value = data.submissionId;
      document.getElementById("edit-log-id").value = data.submissionId;
      document.getElementById("reject-log-id").value = data.submissionId;
  
      document.getElementById("reviewModal").style.display = "block";
    }
  
    // Function to open the Student Info Modal and populate fields
    document.querySelectorAll(".info-btn").forEach(button => {
      button.addEventListener("click", function () {
        const row = this.closest(".student-row");
        openStudentInfoModal({
          pictureUrl: row.dataset.pictureUrl,
          name: row.dataset.name,
          school_id: row.dataset.schoolId,
          form: row.dataset.form,
          hours: row.dataset.hours,
          award: row.dataset.award,
          award_color: row.dataset.awardColor
        });
      });
    });
  
    function openStudentInfoModal(student) {
      document.getElementById("info-student-img").src = student.pictureUrl || '/static/default-profile.png';
      document.getElementById("modal-student-name").textContent = student.name;
      document.getElementById("modal-student-id").textContent = student.school_id;
      document.getElementById("modal-student-form").textContent = student.form;
      document.getElementById("modal-student-hours").textContent = student.hours;
      const awardElem = document.getElementById("modal-student-award");
      awardElem.textContent = student.award;
      awardElem.style.color = student.award_color;
      document.getElementById("studentInfoModal").style.display = "block";
    }
  });
  
  function closeModal() {
    document.getElementById('reviewModal').style.display = 'none';
    if (modalEdited) {
      window.location.reload();
    }
  }
  
  // Open Add Student Modal
  function openAddStudentModal() {
    closeBulkUploadModal();
    document.getElementById('addStudentModal').style.display = 'block';
  }
  
  // Close Add Student Modal
  function closeAddStudentModal() {
    document.getElementById('addStudentModal').style.display = 'none';
  }
  
  function openBulkUploadModal() {
    closeAddStudentModal();
    document.getElementById('bulkUploadModal').style.display = 'block';
  }
  
  function closeBulkUploadModal() {
    document.getElementById('bulkUploadModal').style.display = 'none';
  }
  
  window.onclick = function(event) {
    const modal = document.getElementById('reviewModal');
    const addModal = document.getElementById('addStudentModal');
    const bulkModal = document.getElementById('bulkUploadModal');
    if (event.target === modal) {
      modal.style.display = "none";
    }
    if (event.target === addModal) closeAddStudentModal();
    if (event.target === bulkModal) closeBulkUploadModal();
  }
  
  let modalEdited = false;
  
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
  
  // SEARCH AND PAGINATION FOR ALL STUDENTS TABLE
  document.addEventListener("DOMContentLoaded", function () {
    const rows = Array.from(document.querySelectorAll("#studentsTable tbody tr"));
    const rowsPerPage = 7;
    let currentPage = 1;
    let filteredRows = [...rows];
  
    const pageIndicator = document.getElementById("studentPageIndicator");
    const prevBtn = document.getElementById("studentPrevPage");
    const nextBtn = document.getElementById("studentNextPage");
    const searchInput = document.getElementById("studentSearchInput");
  
    // Function to display rows for the current page
    function showPage(page) {
      const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
      const start = (page - 1) * rowsPerPage;
      const end = start + rowsPerPage;
  
      // Hide all rows, then show only those in the current page range
      rows.forEach(row => row.style.display = "none");
      filteredRows.slice(start, end).forEach(row => row.style.display = "");
  
      pageIndicator.textContent = `Page ${page}`;
      prevBtn.disabled = page === 1;
      nextBtn.disabled = page === totalPages || totalPages === 0;
    }
  
    // Function to filter rows based on the search term and reset pagination
    function updateSearchAndPagination() {
      const searchTerm = searchInput.value.toLowerCase();
  
      filteredRows = rows.filter(row => {
        const schoolId = row.cells[0].textContent.toLowerCase();
        const name = row.cells[1].textContent.toLowerCase();
        const form = row.cells[2].textContent.toLowerCase();
        const award = row.cells[4].textContent.toLowerCase();
        return (
          schoolId.includes(searchTerm) ||
          name.includes(searchTerm) ||
          form.includes(searchTerm) ||
          award.includes(searchTerm)
        );
      });
  
      currentPage = 1;
      showPage(currentPage);
    }
  
    // Event listeners for search input and pagination buttons
    searchInput.addEventListener("input", updateSearchAndPagination);
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        showPage(currentPage);
      }
    });
    nextBtn.addEventListener("click", () => {
      const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
      if (currentPage < totalPages) {
        currentPage++;
        showPage(currentPage);
      }
    });
  
    // Initialize display
    updateSearchAndPagination();
  });
// Update "Choose File" label when file is selected (single student image)
document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("studentImage");
  const fileChosen = document.getElementById("file-chosen");

  if (fileInput && fileChosen) {
    fileInput.addEventListener("change", function () {
      fileChosen.textContent = this.files.length > 0 ? this.files[0].name : "No file chosen";
    });
  }
});

// Update "Choose File" label when bulk upload file is selected
document.addEventListener("DOMContentLoaded", function () {
  const bulkFileInput = document.getElementById("bulkFile");
  const bulkFileChosen = document.getElementById("file-chosen-bulk");

  if (bulkFileInput && bulkFileChosen) {
    bulkFileInput.addEventListener("change", function () {
      bulkFileChosen.textContent = this.files.length > 0 ? this.files[0].name : "No file chosen";
    });
  }
});
  // Open Download Reports Modal
  function openReportModal() {
    document.getElementById('reportModal').style.display = 'block';
  }
  
  // Close Download Reports Modal
  function closeReportModal() {
    document.getElementById('reportModal').style.display = 'none';
  }
  
  // Student Info Modal Functions
  // Modified to accept consistent keys and set the correct image element
  function openStudentInfoModal(student) {
    document.getElementById("info-student-img").src = student.pictureUrl || '/static/default-profile.png';
    document.getElementById("modal-student-name").textContent = student.name;
    document.getElementById("modal-student-id").textContent = student.school_id;
    document.getElementById("modal-student-form").textContent = student.form;
    document.getElementById("modal-student-hours").textContent = student.hours;
    const awardElem = document.getElementById("modal-student-award");
    awardElem.textContent = student.award;
    awardElem.style.color = student.award_color;
    document.getElementById("studentInfoModal").style.display = "block";
  }
  
  function closeStudentInfoModal() {
    document.getElementById("studentInfoModal").style.display = "none";
  }
  
  document.addEventListener("DOMContentLoaded", function () {
    const openDownloadBtn = document.getElementById("openDownloadModal");
    if (openDownloadBtn) {
      openDownloadBtn.addEventListener("click", openReportModal);
    }
  });
  
  // Optionally close modal when clicking outside
  window.addEventListener("click", function (event) {
    const reportModal = document.getElementById("reportModal");
    if (event.target === reportModal) {
      reportModal.style.display = "none";
    }
  });
    // General-purpose sortable columns for any table with .sortable headers
    document.querySelectorAll(".sortable").forEach(header => {
      header.addEventListener("click", () => {
        const table = header.closest("table");
        const tableId = table.id;
        const columnIndex = parseInt(header.dataset.column);
        const currentAscending = header.classList.contains("asc");
  
        document.querySelectorAll(".sortable").forEach(h => h.classList.remove("asc", "desc"));
        header.classList.add(currentAscending ? "desc" : "asc");
  
        sortTableByColumn(tableId, columnIndex, !currentAscending);
      });
  });
  
  // Print student table content in a clean, styled format
  function printTable() {
    const table = document.getElementById('studentsTable');
    const printWindow = window.open('', '', 'width=800,height=600');
  
    printWindow.document.write('<html><head><title>Print Student Table</title><style>');
    printWindow.document.write('table {width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;}');
    printWindow.document.write('th, td {border: 1px solid black; padding: 8px; text-align: center;}');
    printWindow.document.write('th {background-color: #f2f2f2;}');
    printWindow.document.write('</style></head><body>');
    printWindow.document.write('<h2>All Students</h2>');
    printWindow.document.write(table.outerHTML);
    printWindow.document.write('</body></html>');
  
    printWindow.document.close();
    printWindow.print();
  }
  // Remove Student Modal Functions
  function openRemoveStudentModal() {
    document.getElementById('removeStudentModal').style.display = 'block';
  }
  
  function closeRemoveStudentModal() {
    document.getElementById('removeStudentModal').style.display = 'none';
  }
  
function searchStudentForRemoval() {
    const input = document.getElementById('removeSearchInput').value.toLowerCase();
    const students = window.allStudents || [];

    const result = students.find(s =>
      s.name.toLowerCase().includes(input) || s.school_id.toLowerCase().includes(input)
    );

    if (result) {
      console.log("🧪 Selected student for removal:", result);
      document.getElementById('removeStudentName').value = result.name;
      document.getElementById('removeStudentSchoolId').value = result.school_id;
      document.getElementById('removeStudentFormClass').value = result.form;
      document.getElementById('removeStudentHours').value = result.hours;
      document.getElementById('studentIdToRemove').value = result.school_id;
      document.getElementById('studentRemoveResult').style.display = 'block';
    } else {
      document.getElementById('studentRemoveResult').style.display = 'none';
    }
  }
  
  function openBulkRemoveModal() {
    closeRemoveStudentModal(); // Ensure the remove modal is closed
    document.getElementById('bulkRemoveModal').style.display = 'block';
  }
  
  function closeBulkRemoveModal() {
    document.getElementById('bulkRemoveModal').style.display = 'none';
  }
// Open Add Staff Modal
function openAddStaffModal() {
  document.getElementById('addStaffModal').style.display = 'block';
}

// Close Add Staff Modal
function closeAddStaffModal() {
  document.getElementById('addStaffModal').style.display = 'none';
}

function openBulkUploadModalstaff() {
    closeAddStaffModal();
    document.getElementById('bulkUploadModalstaff').style.display = 'block';
  }
  
  // Close Add Staff Modal
function closeBulkUploadModalstaff() {
    document.getElementById('bulkUploadModalstaff').style.display = 'none';
}

// Handle staff image file input change
const staffFileInput = document.getElementById('staffImage');
const staffFileChosen = document.getElementById('file-chosen-staff');

if (staffFileInput) {
  staffFileInput.addEventListener('change', function() {
    if (this.files.length > 0) {
      staffFileChosen.textContent = this.files[0].name;
    } else {
      staffFileChosen.textContent = "No file chosen";
    }
  });
}

function openAddAdminModal() {
document.getElementById("addAdminModal").style.display = "block";
}

function closeAddAdminModal() {
document.getElementById("addAdminModal").style.display = "none";
}

function searchStaffForAdmin() {
const query = document.getElementById("adminSearchInput").value.toLowerCase();
const resultsContainer = document.getElementById("adminSearchResults");
resultsContainer.innerHTML = "";

const staffList = window.allStaff || [];

const filtered = staffList.filter(staff =>
    staff.name.toLowerCase().includes(query) ||
    staff.school_id.toLowerCase().includes(query)
);

if (filtered.length === 0) {
    resultsContainer.innerHTML = "<p>No staff found.</p>";
    return;
}

filtered.forEach(staff => {
    const staffItem = document.createElement("div");
    staffItem.className = "search-result";
    staffItem.innerHTML = `
    <p><strong>${staff.name}</strong> (${staff.school_id})</p>
    <button class="btn btn-primary" onclick="promoteToAdmin('${staff.school_id}')">Make Admin</button>
    `;
    resultsContainer.appendChild(staffItem);
});
}

function promoteToAdmin(schoolId) {
    fetch('/promote-to-admin', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ school_id: schoolId })
    })
    .then(response => response.json())
    .then(data => {
      const messageBox = document.getElementById("adminActionMessage");
  
      if (data.success || data.status === 'success') {
        messageBox.textContent = data.message;
        messageBox.style.display = "block";
        messageBox.style.backgroundColor = "#d4edda";
        messageBox.style.color = "#155724";
        messageBox.style.border = "1px solid #c3e6cb";
  
        document.getElementById("adminSearchInput").value = "";
        searchStaffForAdmin();
        refreshCurrentAdmins();
      } else {
        messageBox.textContent = data.message || "Failed to promote to admin.";
        messageBox.style.display = "block";
        messageBox.style.backgroundColor = "#f8d7da";
        messageBox.style.color = "#721c24";
        messageBox.style.border = "1px solid #f5c6cb";
      }
    })
    .catch(error => {
      console.error("Error promoting to admin:", error);
      const messageBox = document.getElementById("adminActionMessage");
      messageBox.textContent = "An error occurred while promoting to admin.";
      messageBox.style.display = "block";
      messageBox.style.backgroundColor = "#f8d7da";
      messageBox.style.color = "#721c24";
      messageBox.style.border = "1px solid #f5c6cb";
    });
  }

function refreshCurrentAdmins() {
fetch('/api/current_admins')
    .then(res => res.json())
    .then(admins => {
    const list = document.getElementById("currentAdminsList");
    list.innerHTML = "";

    admins.forEach(admin => {
        const item = document.createElement("li");
        item.innerHTML = `
        <span>${admin.name} (${admin.school_id})</span>
        <button class="remove-admin-btn" onclick="removeAdmin('${admin.school_id}')">Remove</button>
        `;
        list.appendChild(item);
    });
    });
}

function removeAdmin(schoolId) {
    fetch('/admin/remove', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ school_id: schoolId })
    })
    .then(response => response.json())
    .then(data => {
      const messageBox = document.getElementById("adminActionMessage");
  
      if (messageBox) {
        messageBox.textContent = data.message;
        messageBox.className = ""; // clear previous classes
        messageBox.classList.add(data.status === 'success' ? 'success' : 'error');
        messageBox.style.display = 'block';
      }
  
      if (data.status === 'success') {
        refreshCurrentAdmins();
      }
    })
    .catch(error => {
      const messageBox = document.getElementById("adminActionMessage");
      if (messageBox) {
        messageBox.textContent = "An unexpected error occurred.";
        messageBox.className = "error";
        messageBox.style.display = 'block';
      }
      console.error("Error removing admin:", error);
    });
  }