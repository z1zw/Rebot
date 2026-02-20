class Tile {
    constructor(gridElement, value = Math.random() > 0.5 ? 2 : 4) {
        this.tileElement = document.createElement("div");
        this.tileElement.classList.add("tile");
        gridElement.append(this.tileElement);
        this.setValue(value);
        this.x = 0;
        this.y = 0;
        this.waitingForDeletion = false;
        this.mergedFrom = null;
    }

    setValue(value) {
        this.value = value;
        this.tileElement.textContent = value;
        const bgLightness = 100 - Math.log2(value) * 9;
        this.tileElement.style.setProperty("--bg-lightness", `${bgLightness}%`);
        this.tileElement.style.setProperty("--text-lightness", `${bgLightness < 50 ? 90 : 10}%`);
    }

    setPosition(x, y, animate = true) {
        this.x = x;
        this.y = y;
        if (animate) {
            this.tileElement.style.transition = "100ms";
        } else {
            this.tileElement.style.transition = "none";
        }
        this.tileElement.style.setProperty("--x", x);
        this.tileElement.style.setProperty("--y", y);
    }

    removeFromDOM() {
        this.tileElement.remove();
    }

    waitForDeletion() {
        this.waitingForDeletion = true;
    }

    animateMerge() {
        this.tileElement.classList.add("merged");
        setTimeout(() => {
            this.tileElement.classList.remove("merged");
        }, 200);
    }

    animateAppear() {
        this.tileElement.classList.add("new");
        setTimeout(() => {
            this.tileElement.classList.remove("new");
        }, 200);
    }
}