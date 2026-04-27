(function () {
    "use strict";

    var brand = document.querySelector(".brand");
    var brandMark = document.querySelector(".brand-mark");
    var dice = document.querySelector(".brand-mark svg");

    if (!brand || !brandMark || !dice) {
        return;
    }

    var isRolling = false;

    function randomFace() {
        return Math.floor(Math.random() * 6) + 1;
    }

    function randomTurn(min, max) {
        var degrees = Math.floor(Math.random() * (max - min + 1)) + min;
        return degrees + "deg";
    }

    function rollDice() {
        if (isRolling) {
            return;
        }

        isRolling = true;

        var nextFace = randomFace();
        var endTurn = randomTurn(810, 1260);
        var endDegrees = parseInt(endTurn, 10);
        var midDegrees = Math.round(endDegrees * 0.62);

        brandMark.style.setProperty("--roll-mid", midDegrees + "deg");
        brandMark.style.setProperty("--roll-end", endTurn);
        brandMark.classList.remove("is-rolling");
        void brandMark.offsetWidth;
        brandMark.classList.add("is-rolling");

        var fallbackTimer = window.setTimeout(function () {
            brandMark.classList.remove("is-rolling");
            dice.dataset.face = String(nextFace);
            isRolling = false;
        }, 700);

        function onAnimationEnd(event) {
            if (event.animationName !== "brand-dice-roll") {
                return;
            }

            window.clearTimeout(fallbackTimer);
            brandMark.classList.remove("is-rolling");
            dice.dataset.face = String(nextFace);
            isRolling = false;
            brandMark.removeEventListener("animationend", onAnimationEnd);
        }

        brandMark.addEventListener("animationend", onAnimationEnd);
    }

    brand.addEventListener("mouseenter", rollDice);
    brand.addEventListener("focus", rollDice);
})();
