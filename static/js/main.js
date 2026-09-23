// Main Application JavaScript: Real-Time Heartbeat & Live Active Polling

document.addEventListener("DOMContentLoaded", function () {
    // 1. Send Heartbeat to keep session active
    function sendHeartbeat() {
        fetch("/api/heartbeat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            }
        }).catch(err => console.debug("Heartbeat ping:", err));
    }

    // Send heartbeat immediately on load, then every 20 seconds
    sendHeartbeat();
    setInterval(sendHeartbeat, 20000);

    // 2. Real-time Active Customers Polling for Segmentation and Admin Dashboards
    const activeContainer = document.getElementById("active-customers-list");
    const activeCountElem = document.getElementById("active-customers-count");

    if (activeContainer) {
        function pollActiveCustomers() {
            fetch("/api/active-customers")
                .then(response => {
                    if (!response.ok) throw new Error("Network response was not ok");
                    return response.json();
                })
                .then(data => {
                    if (activeCountElem) {
                        activeCountElem.textContent = data.active_count;
                    }

                    if (activeContainer) {
                        if (data.customers.length === 0) {
                            activeContainer.innerHTML = `
                                <div class="col-12 text-center py-4 text-muted">
                                    <i class="bi bi-people fs-2 d-block mb-2"></i>
                                    No active customers right now.
                                </div>
                            `;
                            return;
                        }

                        let html = "";
                        data.customers.forEach(cust => {
                            const badgeClass = getBadgeClass(cust.segment_label);
                            const currentUserTag = cust.is_current_user ? '<span class="badge bg-secondary ms-2">You</span>' : '';
                            
                            html += `
                                <div class="col-md-6 col-lg-4 mb-3">
                                    <div class="card card-custom h-100 p-3 border-start border-4 ${cust.is_current_user ? 'border-primary' : 'border-info'}">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <div class="d-flex align-items-center gap-2 mb-1">
                                                    <span class="pulse-indicator"></span>
                                                    <h6 class="mb-0 fw-bold text-dark">${escapeHtml(cust.name)} ${currentUserTag}</h6>
                                                </div>
                                                <span class="badge ${badgeClass} text-uppercase px-2 py-1 mt-1">
                                                    ${escapeHtml(cust.segment_label)}
                                                </span>
                                            </div>
                                            <div class="text-end text-muted small">
                                                <span class="badge bg-light text-dark border">
                                                    <i class="bi bi-broadcast text-success me-1"></i> Active
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        activeContainer.innerHTML = html;
                    }
                })
                .catch(err => console.debug("Active polling error:", err));
        }

        // Poll every 3 seconds for near-real-time responsiveness
        setInterval(pollActiveCustomers, 3000);
    }

    // Badge styling helper
    function getBadgeClass(label) {
        switch (label) {
            case "HIGH VALUE CUSTOMER": return "badge-high-value";
            case "REGULAR CUSTOMER": return "badge-regular";
            case "NEW CUSTOMER": return "badge-new";
            case "AT-RISK CUSTOMER": return "badge-at-risk";
            case "DISCOUNT SEEKER": return "badge-discount-seeker";
            default: return "bg-info";
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Auto-dismiss alerts after 6 seconds
    setTimeout(function () {
        const alerts = document.querySelectorAll(".alert-dismissible");
        alerts.forEach(function (alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 6000);
});
