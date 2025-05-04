document.addEventListener("DOMContentLoaded", function () {
  console.log("Custom script loaded.");
  // For the discount preview in the add_book and edit_book forms:
  const priceInput = document.getElementById("price");
  const discountInput = document.getElementById("discount_percentage");
  const previewSpan = document.getElementById("discountedPricePreview");
  
  if (priceInput && discountInput && previewSpan) {
    function updatePreview() {
      const price = parseFloat(priceInput.value);
      const discount = parseFloat(discountInput.value);
      if (!isNaN(price) && !isNaN(discount)) {
        const discounted = price * (1 - discount / 100);
        previewSpan.textContent = "Discounted Price: $" + discounted.toFixed(2);
      } else {
        previewSpan.textContent = "";
      }
    }
    priceInput.addEventListener("input", updatePreview);
    discountInput.addEventListener("input", updatePreview);
  }
});
