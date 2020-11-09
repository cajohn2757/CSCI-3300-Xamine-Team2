const toggleColorMode = e => {
    if(e.currentTarget.classList.contains("light-hidden")) {

        document.documentElement.setAttribute("color-mode", "light");

        localStorage.setItem("color-mode", "light");
        return;
    }

    document.documentElement.setAttribute("color-mode", "dark");

    localStorage.setItem("color-mode", "dark");
};

const toggleColorButtons = document.querySelectorAll(".colorbutton");


toggleColorButtons.forEach(btn => {
    btn.addEventListener("click", toggleColorMode);
});