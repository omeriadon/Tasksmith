// Course Dialog Functions
function showCourseDialog() {
  document.getElementById("courseDialog").style.display = "flex";
  document.getElementById("content").classList.add("blur");

  // Load users when dialog opens
  if (typeof loadUsers === "function") {
    loadUsers();
  }
}

function closeCourseDialog() {
  document.getElementById("courseDialog").style.display = "none";
  document.getElementById("content").classList.remove("blur");
}

// Task Dialog Functions
function showTaskDialog() {
  document.getElementById("taskDialog").style.display = "flex";
  document.getElementById("content").classList.add("blur");

  // Load courses when dialog opens
  if (typeof loadCourses === "function") {
    loadCoursesForTasks();
  }
}

function closeTaskDialog() {
  document.getElementById("taskDialog").style.display = "none";
  document.getElementById("content").classList.remove("blur");
}
