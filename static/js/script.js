// ========================================================
// SCRIPT UTAMA - SEMUA FUNGSI (FIXED & CLEAN)
// ========================================================

let isLoggedIn = false;
let isGenerating = false;
let progressTimer = null;
let progressAnimTimer = null;
let displayedProgress = 0;
let targetProgress = 0;
let activeTaskId = null;
let cancelRequested = false;
const SKIP_ENTRY_ANIM_KEY = "skip_entry_anim_once";
let skipEntryAnimationForPage = false;

function markSkipEntryAnimation() {
    try {
        sessionStorage.setItem(SKIP_ENTRY_ANIM_KEY, "1");
    } catch (e) {
        console.warn("sessionStorage unavailable:", e);
    }
}

function consumeSkipEntryAnimationFlag() {
    try {
        const shouldSkip = sessionStorage.getItem(SKIP_ENTRY_ANIM_KEY) === "1";
        if (shouldSkip) {
            sessionStorage.removeItem(SKIP_ENTRY_ANIM_KEY);
        }
        return shouldSkip;
    } catch (e) {
        console.warn("sessionStorage unavailable:", e);
        return false;
    }
}

skipEntryAnimationForPage = consumeSkipEntryAnimationFlag();

function runIndexEntryAnimation() {
    const mainCard = document.querySelector(".main-card");
    const toolCards = document.querySelectorAll(".tools-grid .tool-card");
    if (!mainCard || toolCards.length === 0) return;

    document.body.classList.remove("index-enter");
    void document.body.offsetWidth;
    document.body.classList.add("index-enter");
}

function runGenerateEntryAnimation() {
    const generateBlocks = document.querySelectorAll(".main-card .content-area, .main-card .input-title");
    if (generateBlocks.length < 2) return;

    document.body.classList.remove("generate-enter");
    void document.body.offsetWidth;
    document.body.classList.add("generate-enter");
}

function runPageEntryAnimation() {
    if (skipEntryAnimationForPage) {
        document.body.classList.remove("index-enter", "generate-enter");
        return;
    }

    runIndexEntryAnimation();
    runGenerateEntryAnimation();
}

function updateAuthUI() {
    const userIcon = document.getElementById("userIcon");
    if (!userIcon) return;
    userIcon.classList.toggle("active", isLoggedIn);
}

function normalizeTitleLine(text) {
    if (!text) return "";
    const cleaned = text.replace(/^\s*\d+\.\s*/, "").trim();
    if (!cleaned) return "";
    return cleaned.replace(/\b([A-Za-z])([A-Za-z]*)\b/g, (_, firstChar, rest) => {
        return firstChar.toUpperCase() + rest.toLowerCase();
    });
}

function normalizeTextareaInput(inputArea) {
    if (!inputArea) return [];
    const lines = inputArea.value
        .split("\n")
        .map(normalizeTitleLine)
        .filter(line => line !== "");
    inputArea.value = lines.join("\n");
    return lines;
}

function setArticleStatus(index, status) {
    const icon = document.querySelector(`#art${index} .status i`);
    if (!icon) return;

    if (status === "running") {
        icon.className = "fa-solid fa-spinner fa-spin running";
    } else if (status === "gemini_done") {
        icon.className = "fa-solid fa-spinner fa-spin running";
    } else if (status === "success") {
        icon.className = "fa-solid fa-circle-check completed";
    } else if (status === "error") {
        icon.className = "fa-solid fa-circle-xmark failed";
    } else if (status === "cancelled") {
        icon.className = "fa-solid fa-ban failed";
    } else {
        icon.className = "fa-regular fa-circle";
    }
}

function stopProgressPolling() {
    if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
    }
}

function setProgressUI(percent) {
    const safePercent = Math.max(0, Math.min(100, percent));
    const progressBar = document.getElementById("reportProgress");
    const progressPercent = document.getElementById("progressPercent");
    if (progressBar) progressBar.style.width = `${safePercent}%`;
    if (progressPercent) progressPercent.textContent = `${Math.round(safePercent)}%`;
}

function stopProgressAnimation() {
    if (progressAnimTimer) {
        clearInterval(progressAnimTimer);
        progressAnimTimer = null;
    }
}

function startProgressAnimation() {
    stopProgressAnimation();
    progressAnimTimer = setInterval(() => {
        const diff = targetProgress - displayedProgress;
        if (Math.abs(diff) < 0.2) {
            displayedProgress = targetProgress;
            setProgressUI(displayedProgress);
            if (!isGenerating) {
                stopProgressAnimation();
            }
            return;
        }

        const step = Math.max(0.35, Math.min(2.2, Math.abs(diff) * 0.15));
        displayedProgress += diff > 0 ? step : -step;
        setProgressUI(displayedProgress);
    }, 60);
}

function startProgressPolling(taskId) {
    stopProgressPolling();
    startProgressAnimation();

    const tick = () => {
        fetch(`/progress/${taskId}`)
            .then(res => res.json())
            .then(task => {
                if (!task.items) return;

                const items = task.items;
                const total = items.length;
                let doneCount = 0;
                let totalProgress = 0;

                items.forEach((it, idx) => {
                    setArticleStatus(idx + 1, it.status);
                    let itemProgress = Number(it.progress);
                    if (!Number.isFinite(itemProgress)) {
                        if (it.status === "gemini_done") itemProgress = 50;
                        else if (it.status === "success" || it.status === "error") itemProgress = 100;
                        else itemProgress = 0;
                    }
                    itemProgress = Math.max(0, Math.min(100, itemProgress));
                    totalProgress += itemProgress;

                    if (it.status === "success" || it.status === "error" || it.status === "cancelled") {
                        doneCount += 1;
                    }
                });

                const percent = total ? Math.round(totalProgress / total) : 0;
                const progressCount = document.getElementById("progressCount");
                targetProgress = percent;

                if (progressCount) progressCount.textContent = `Artikel [${doneCount}/${total}]`;

                if (task.done) {
                    stopProgressPolling();
                    isGenerating = false;
                    activeTaskId = null;
                    cancelRequested = false;
                }
            })
            .catch(err => {
                console.error("Error polling progress:", err);
            });
    };

    tick();
    progressTimer = setInterval(tick, 1000);
}

document.addEventListener("DOMContentLoaded", function () {
    console.log("Sistem Siap...");
    runPageEntryAnimation();

    // 1. LOGIKA SIDEBAR
    const navToggle = document.querySelector(".nav-toggle");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.querySelector(".overlay");
    const closeSidebar = document.querySelector(".close-sidebar");

    if (navToggle && sidebar) {
        navToggle.addEventListener("click", () => sidebar.classList.add("active"));
    }
    if (closeSidebar && sidebar) {
        closeSidebar.addEventListener("click", () => sidebar.classList.remove("active"));
    }
    if (overlay && sidebar) {
        overlay.addEventListener("click", () => sidebar.classList.remove("active"));
    }

    // 2. JAM REALTIME
    function updateTime() {
        const timeEl = document.getElementById("time");
        if (!timeEl) return;
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString("en-GB");
    }
    setInterval(updateTime, 1000);
    updateTime();

    // 3. CEK STATUS LOGIN
    fetch("/check_login")
        .then(res => res.json())
        .then(data => {
            isLoggedIn = !!data.logged_in;
            updateAuthUI();
        })
        .catch(err => console.error("Error check login:", err));

    // ENTER untuk login
    const usernameEl = document.getElementById("username");
    const passwordEl = document.getElementById("password");
    [usernameEl, passwordEl].forEach((el) => {
        if (!el) return;
        el.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                window.login();
            }
        });
    });

    // CTRL+ENTER untuk generate
    const inputArea = document.getElementById("input");
    if (inputArea) {
        inputArea.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && e.ctrlKey) {
                e.preventDefault();
                window.kirim();
            }
        });

        inputArea.addEventListener("blur", function () {
            normalizeTextareaInput(inputArea);
        });
    }
});

window.addEventListener("pageshow", function () {
    runPageEntryAnimation();
});

// ========================================================
// FUNGSI GLOBAL
// ========================================================

window.openLogin = function () {
    const popup = document.getElementById("loginPopup");
    if (popup) popup.classList.add("active");
};

window.closeLogin = function (skipAnimation = false) {
    const popup = document.getElementById("loginPopup");
    if (popup) popup.classList.remove("active");
    if (skipAnimation) markSkipEntryAnimation();
};

window.togglePassword = function () {
    const pass = document.getElementById("password");
    const icon = document.querySelector(".toggle-pass");
    if (!pass || !icon) return;

    if (pass.type === "password") {
        pass.type = "text";
        icon.classList.replace("fa-eye-slash", "fa-eye");
    } else {
        pass.type = "password";
        icon.classList.replace("fa-eye", "fa-eye-slash");
    }
};

window.closeAuthWarning = function () {
    const authWarning = document.getElementById("authWarning");
    if (authWarning) authWarning.style.display = "none";
};

window.closeReport = function () {
    if (isGenerating) {
        cancelRequested = true;
        if (activeTaskId) {
            fetch(`/cancel/${activeTaskId}`, { method: "POST" })
                .catch(err => console.error("Error cancel task:", err));
        }
    }

    const reportPopup = document.getElementById("reportPopup");
    if (reportPopup) reportPopup.classList.remove("active");
    stopProgressPolling();
    stopProgressAnimation();
    isGenerating = false;
    activeTaskId = null;
};

window.login = function () {
    const userEl = document.getElementById("username");
    const passEl = document.getElementById("password");
    const loginBtn = document.querySelector(".login-submit");
    if (!userEl || !passEl) return;
    if (loginBtn && loginBtn.classList.contains("loading")) return;

    const user = userEl.value;
    const pass = passEl.value;

    if (!user || !pass) {
        alert("Isi username dan password!");
        return;
    }

    if (loginBtn) {
        loginBtn.classList.add("loading");
        loginBtn.disabled = true;
    }

    setTimeout(() => {
        fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    isLoggedIn = true;
                    updateAuthUI();
                    closeLogin(true);
                    location.reload();
                } else {
                    alert("Username atau Password Salah!");
                    if (loginBtn) {
                        loginBtn.classList.remove("loading");
                        loginBtn.disabled = false;
                    }
                }
            })
            .catch(err => {
                console.error("Error Login:", err);
                if (loginBtn) {
                    loginBtn.classList.remove("loading");
                    loginBtn.disabled = false;
                }
            });
    }, 2000);
};

window.logout = function () {
    fetch("/logout")
        .then(res => res.json())
        .then(data => {
            if (data.status === "logout") {
                isLoggedIn = false;
                updateAuthUI();
                markSkipEntryAnimation();
                location.reload();
            }
        })
        .catch(err => console.error("Error Logout:", err));
};

window.kirim = function () {
    if (isGenerating) return;
    isGenerating = true;
    cancelRequested = false;

    if (!isLoggedIn) {
        const authWarning = document.getElementById("authWarning");
        if (authWarning) authWarning.style.display = "flex";
        isGenerating = false;
        return;
    }

    const inputArea = document.getElementById("input");
    if (!inputArea) {
        isGenerating = false;
        return;
    }

    const judulList = normalizeTextareaInput(inputArea);
    if (judulList.length === 0) {
        alert("Masukkan minimal satu judul!");
        isGenerating = false;
        return;
    }

    const articleListContainer = document.querySelector(".article-list");
    if (articleListContainer) {
        articleListContainer.innerHTML = "";
        judulList.forEach((judul, index) => {
            const articleDiv = document.createElement("div");
            articleDiv.className = "article";
            articleDiv.id = `art${index + 1}`;
            articleDiv.innerHTML = `
                <span class="title">Artikel ${index + 1}</span>
                <span class="status"><i class="fa-regular fa-circle"></i></span>
            `;
            articleListContainer.appendChild(articleDiv);
        });
    }

    const progressCount = document.getElementById("progressCount");
    displayedProgress = 0;
    targetProgress = 0;

    if (progressCount) progressCount.textContent = `Artikel [0/${judulList.length}]`;
    setProgressUI(0);

    const reportPopup = document.getElementById("reportPopup");
    if (reportPopup) reportPopup.classList.add("active");

    fetch("/proses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ judul_list: judulList })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === "running" && data.task_id) {
                activeTaskId = data.task_id;
                if (cancelRequested) {
                    fetch(`/cancel/${activeTaskId}`, { method: "POST" })
                        .catch(err => console.error("Error cancel task:", err));
                    isGenerating = false;
                    activeTaskId = null;
                    return;
                }
                startProgressPolling(data.task_id);
            } else if (data.status === "unauthorized") {
                alert("Sesi habis, silakan login ulang.");
                window.openLogin();
                isGenerating = false;
                activeTaskId = null;
                cancelRequested = false;
            } else {
                isGenerating = false;
                activeTaskId = null;
                cancelRequested = false;
            }
        })
        .catch(err => {
            console.error("Error Proses:", err);
            alert("Gagal menghubungi server.");
            isGenerating = false;
            activeTaskId = null;
            cancelRequested = false;
        });
};
