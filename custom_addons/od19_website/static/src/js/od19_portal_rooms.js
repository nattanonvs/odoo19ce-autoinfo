/** Auto-Info Employee Portal — the "when is this room taken" popup. */
(function () {
    'use strict';

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text) {
            node.textContent = text;
        }
        return node;
    }

    function buildSection(label, icon, rows, emptyText) {
        var section = el('div', 'od19-schedule-section');
        var heading = el('div', 'od19-subheading');
        heading.appendChild(el('i', 'fa ' + icon + ' me-1'));
        heading.appendChild(document.createTextNode(label));
        section.appendChild(heading);

        if (!rows.length) {
            section.appendChild(el('p', 'text-muted small mb-0', emptyText));
            return section;
        }

        var table = el('table', 'table table-sm od19-schedule-table mb-0');
        var headRow = el('tr');
        ['วันที่', 'เวลา', 'หัวข้อ', 'ผู้จอง', 'สถานะ'].forEach(function (title) {
            headRow.appendChild(el('th', null, title));
        });
        var thead = el('thead');
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = el('tbody');
        rows.forEach(function (row) {
            var tr = el('tr');
            tr.appendChild(el('td', 'text-nowrap', row.date));
            tr.appendChild(el('td', 'text-nowrap', row.start + ' - ' + row.end));
            tr.appendChild(el('td', null, row.name));
            tr.appendChild(el('td', null, row.organizer));
            var state = el('td');
            state.appendChild(el('span', 'od19-room-badge od19-badge-reserved', row.state_label));
            tr.appendChild(state);
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        section.appendChild(table);
        return section;
    }

    function render(holder, payload) {
        holder.textContent = '';

        var status = el('div', 'od19-schedule-status ' + (payload.busy_now ? 'is-busy' : 'is-free'));
        status.appendChild(el('i', 'fa ' + (payload.busy_now ? 'fa-circle' : 'fa-check-circle') + ' me-1'));
        status.appendChild(document.createTextNode(payload.busy_now ? 'ขณะนี้ห้องถูกใช้งานอยู่' : 'ขณะนี้ห้องว่าง'));
        holder.appendChild(status);

        holder.appendChild(buildSection(
            'การจองล่วงหน้า', 'fa-calendar-check-o', payload.upcoming, 'ยังไม่มีการจองล่วงหน้า'
        ));
        holder.appendChild(buildSection(
            'ย้อนหลัง ' + payload.window_months + ' เดือน', 'fa-history', payload.history,
            'ไม่มีการใช้งานย้อนหลังในช่วงนี้'
        ));
    }

    function load(holder) {
        holder.dataset.loaded = '1';
        var url = '/employee-portal/room-schedule?room_id=' + encodeURIComponent(holder.dataset.roomId);
        fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (payload) {
                render(holder, payload);
            })
            .catch(function () {
                // The tiles and the booking form keep working, so a failed
                // fetch only loses the schedule itself.
                holder.textContent = '';
                holder.appendChild(el(
                    'p', 'text-danger small mb-0',
                    'ไม่สามารถโหลดตารางการใช้ห้องได้ กรุณาลองใหม่อีกครั้ง'
                ));
            });
    }

    document.addEventListener('show.bs.modal', function (event) {
        var holder = event.target.querySelector('.od19-room-schedule');
        if (holder && !holder.dataset.loaded) {
            load(holder);
        }
    });
})();
