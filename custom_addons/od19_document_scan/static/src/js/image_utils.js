// Copyright 2026 OD19
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

/**
 * Camera helpers shared by the scan wizard, the chatter and the field widget.
 *
 * Everything is done client-side so the photos stay small before they ever
 * reach the server: we downscale on a canvas and re-encode them as JPEG.
 */

/** Default compression settings: good enough to read a document, small on disk. */
export const DEFAULT_PHOTO_PARAMS = {
    maxWidth: 1600,
    maxHeight: 1600,
    quality: 0.82,
    mimeType: "image/jpeg",
};

/**
 * Is a usable camera API available? ``getUserMedia`` only works in a secure
 * context (https or localhost), so we check that too.
 *
 * @returns {boolean}
 */
export function isCameraSupported() {
    return Boolean(
        window.isSecureContext &&
            navigator.mediaDevices &&
            typeof navigator.mediaDevices.getUserMedia === "function"
    );
}

/**
 * @param {Blob} blob
 * @returns {Promise<string>} a ``data:`` URL
 */
export function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
    });
}

/**
 * @param {Blob} blob
 * @returns {Promise<string>} the base64 payload without the ``data:`` prefix
 */
export function blobToBase64(blob) {
    return blobToDataUrl(blob).then((url) => String(url).split(",")[1] || "");
}

/**
 * @param {Blob} blob
 * @returns {Promise<HTMLImageElement>}
 */
function loadImage(blob) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const url = URL.createObjectURL(blob);
        img.onload = () => {
            URL.revokeObjectURL(url);
            resolve(img);
        };
        img.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error("Could not read the image"));
        };
        img.src = url;
    });
}

/**
 * Downscale and recompress an image blob.
 *
 * @param {Blob} blob
 * @param {Object} [params] see :js:data:`DEFAULT_PHOTO_PARAMS`
 * @returns {Promise<Blob>}
 */
export async function compressImageBlob(blob, params = {}) {
    if (!blob || !blob.type || !blob.type.startsWith("image/")) {
        return blob;
    }
    const { maxWidth, maxHeight, quality, mimeType } = {
        ...DEFAULT_PHOTO_PARAMS,
        ...params,
    };
    const img = await loadImage(blob);
    const ratio = Math.min(1, maxWidth / img.width, maxHeight / img.height);
    const width = Math.max(1, Math.round(img.width * ratio));
    const height = Math.max(1, Math.round(img.height * ratio));

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    if (mimeType === "image/jpeg") {
        // Paint a white background so transparent PNGs do not turn black.
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
    }
    ctx.drawImage(img, 0, 0, width, height);

    const out = await new Promise((resolve) => canvas.toBlob(resolve, mimeType, quality));
    return out || blob;
}

/**
 * Grab the current frame of a live ``<video>`` element as a compressed blob.
 *
 * @param {HTMLVideoElement} videoEl
 * @param {Object} [params]
 * @returns {Promise<Blob>}
 */
export async function captureVideoFrame(videoEl, params = {}) {
    const width = videoEl.videoWidth;
    const height = videoEl.videoHeight;
    if (!width || !height) {
        throw new Error("The camera image is not ready yet");
    }
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d").drawImage(videoEl, 0, 0, width, height);
    const raw = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95));
    return compressImageBlob(raw, params);
}

/**
 * Build a sortable, human-readable file name for a captured photo.
 *
 * @param {string} [prefix="scan"]
 * @returns {string}
 */
export function photoFilename(prefix = "scan") {
    const d = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return [
        prefix,
        `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`,
        `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`,
    ].join("-") + ".jpg";
}
