(() => {
    const button = document.getElementById("back-to-top");
    if (!button) return;

    const toggle = () => {
        const shouldShow = window.scrollY > 300;
        if (shouldShow) {
            button.classList.remove("hidden");
            button.classList.add("flex");
        } else {
            button.classList.add("hidden");
            button.classList.remove("flex");
        }
    };

    let ticking = false;
    window.addEventListener(
        "scroll",
        () => {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(() => {
                toggle();
                ticking = false;
            });
        },
        { passive: true }
    );

    button.addEventListener("click", () => {
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
    });

    toggle();
})();
