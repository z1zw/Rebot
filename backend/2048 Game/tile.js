class Tile {
    constructor(value, row, col) {
        this.value = value || 0;
        this.row = row;
        this.col = col;
        this.previousPosition = null;
        this.mergedFrom = null;
        this.isNew = true;
        this.animation = null;
    }

    savePosition() {
        this.previousPosition = { row: this.row, col: this.col };
    }

    updatePosition(position) {
        this.row = position.row;
        this.col = position.col;
    }

    getPosition() {
        return { row: this.row, col: this.col };
    }

    setValue(value) {
        this.value = value;
        this.isNew = false;
    }

    getValue() {
        return this.value;
    }

    setMergedFrom(tiles) {
        this.mergedFrom = tiles;
    }

    getMergedFrom() {
        return this.mergedFrom;
    }

    isMerged() {
        return this.mergedFrom !== null;
    }

    clearMerge() {
        this.mergedFrom = null;
    }

    setAnimation(animationType, duration) {
        this.animation = {
            type: animationType,
            startTime: Date.now(),
            duration: duration
        };
    }

    updateAnimation() {
        if (!this.animation) return false;
        const elapsed = Date.now() - this.animation.startTime;
        if (elapsed >= this.animation.duration) {
            this.animation = null;
            return false;
        }
        return true;
    }

    getAnimationProgress() {
        if (!this.animation) return 1;
        const elapsed = Date.now() - this.animation.startTime;
        return Math.min(elapsed / this.animation.duration, 1);
    }

    clearAnimation() {
        this.animation = null;
    }

    hasAnimation() {
        return this.animation !== null;
    }

    getAnimationType() {
        return this.animation ? this.animation.type : null;
    }

    isNewTile() {
        return this.isNew;
    }

    markAsOld() {
        this.isNew = false;
    }

    clone() {
        const newTile = new Tile(this.value, this.row, this.col);
        newTile.previousPosition = this.previousPosition ? { ...this.previousPosition } : null;
        newTile.mergedFrom = this.mergedFrom;
        newTile.isNew = this.isNew;
        newTile.animation = this.animation ? { ...this.animation } : null;
        return newTile;
    }

    serialize() {
        return {
            value: this.value,
            row: this.row,
            col: this.col,
            previousPosition: this.previousPosition,
            mergedFrom: this.mergedFrom,
            isNew: this.isNew,
            animation: this.animation
        };
    }

    static deserialize(data) {
        const tile = new Tile(data.value, data.row, data.col);
        tile.previousPosition = data.previousPosition;
        tile.mergedFrom = data.mergedFrom;
        tile.isNew = data.isNew;
        tile.animation = data.animation;
        return tile;
    }
}