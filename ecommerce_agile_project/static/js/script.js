document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity .5s";
      setTimeout(() => el.remove(), 500);
    }, 3500);
  });

  document.querySelectorAll("input[type=number]").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.min && Number(input.value) < Number(input.min)) input.value = input.min;
      if (input.max && Number(input.value) > Number(input.max)) input.value = input.max;
    });
  });
});
