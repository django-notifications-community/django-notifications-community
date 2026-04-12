var notify_badge_class;
var notify_menu_class;
var notify_api_url;
var notify_fetch_count;
var notify_unread_url;
var notify_mark_all_unread_url;
var notify_refresh_period = 15000;
// Set notify_mark_as_read to true to mark notifications as read when fetched
var notify_mark_as_read = false;

let consecutive_misfires = 0;
const registered_functions = [];

function fill_notification_badge(data) {
    for (const badge of document.getElementsByClassName(notify_badge_class)) {
        badge.innerHTML = data.unread_count;
    }
}

function fill_notification_list(data) {
    const messages = data.unread_list.map((item) => {
        let message = '';

        if (item.actor) {
            message = item.actor;
        }
        if (item.verb) {
            message += ` ${item.verb}`;
        }
        if (item.target) {
            message += ` ${item.target}`;
        }
        if (item.timestamp) {
            message += ` ${item.timestamp}`;
        }
        return `<li>${message}</li>`;
    }).join('');

    for (const menu of document.getElementsByClassName(notify_menu_class)) {
        menu.innerHTML = messages;
    }
}

function register_notifier(func) {
    registered_functions.push(func);
}

async function fetch_api_data() {
    if (registered_functions.length > 0) {
        let params = `?max=${notify_fetch_count}`;
        if (notify_mark_as_read) {
            params += '&mark_as_read=true';
        }

        try {
            const response = await fetch(notify_api_url + params);
            if (response.ok) {
                consecutive_misfires = 0;
                const data = await response.json();
                for (const func of registered_functions) {
                    func(data);
                }
            } else {
                consecutive_misfires++;
            }
        } catch {
            consecutive_misfires++;
        }
    }

    if (consecutive_misfires < 10) {
        setTimeout(fetch_api_data, notify_refresh_period);
    } else {
        for (const badge of document.getElementsByClassName(notify_badge_class)) {
            badge.innerHTML = '!';
            badge.title = 'Connection lost!';
        }
    }
}

function _resolveCallback(name) {
    var parts = name.split('.');
    var obj = window;
    for (var i = 0; i < parts.length; i++) {
        obj = obj[parts[i]];
        if (typeof obj === 'undefined') {
            return undefined;
        }
    }
    return obj;
}

function _initNotifyConfig() {
    var el = document.getElementById('notify-config');
    if (!el) {
        return;
    }
    var config;
    try {
        config = JSON.parse(el.textContent);
    } catch (e) {
        return;
    }

    notify_badge_class = config.badgeClass;
    notify_menu_class = config.menuClass;
    notify_api_url = config.apiUrl;
    notify_fetch_count = config.fetchCount;
    notify_unread_url = config.unreadUrl;
    notify_mark_all_unread_url = config.markAllUnreadUrl;
    notify_refresh_period = config.refreshPeriod;
    notify_mark_as_read = config.markAsRead;

    if (config.callbacks) {
        for (var i = 0; i < config.callbacks.length; i++) {
            var fn = _resolveCallback(config.callbacks[i]);
            if (typeof fn === 'function') {
                register_notifier(fn);
            }
        }
    }

    setTimeout(fetch_api_data, 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initNotifyConfig);
} else {
    _initNotifyConfig();
}
