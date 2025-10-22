// highlight current nav link
document.addEventListener("DOMContentLoaded", function() {
  const currentPage = window.location.pathname.split("/").pop(); // e.g., profile.html
  const navLinks = document.querySelectorAll(".navbar nav a");

  navLinks.forEach(link => {
    if (link.getAttribute("href") === currentPage) {
      link.classList.add("active");
    }
  });
});