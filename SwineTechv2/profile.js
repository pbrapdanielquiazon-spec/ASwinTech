const uploadImg = document.getElementById("upload-img");
const previewImg = document.getElementById("preview-img");

if (uploadImg) {
  uploadImg.addEventListener("change", function() {
    const file = this.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function(e) {
        previewImg.src = e.target.result;
      }
      reader.readAsDataURL(file);
    }
  });
}