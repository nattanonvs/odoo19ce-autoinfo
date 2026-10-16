/** Auto-Info Product Catalog — department filter + scroll reveal. */
(function () {
    'use strict';

    function init() {
        // Department filter (catalog page only)
        var root = document.querySelector('.od19-pc');
        if (root) {
            var pills = root.querySelectorAll('.od19-pc-pill');
            var depts = root.querySelectorAll('.od19-pc-dept');

            pills.forEach(function (pill) {
                pill.addEventListener('click', function () {
                    var filter = pill.getAttribute('data-filter');
                    pills.forEach(function (p) {
                        p.classList.toggle('active', p === pill);
                    });
                    depts.forEach(function (section) {
                        var show = filter === 'all' || section.getAttribute('data-dept') === filter;
                        section.classList.toggle('od19-pc-hidden', !show);
                    });
                });
            });
        }

        // Reveal on scroll (any page using the reveal class)
        var items = document.querySelectorAll('.od19-pc-reveal');
        if (!items.length) {
            return;
        }
        if ('IntersectionObserver' in window) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('od19-pc-in');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.12 });
            items.forEach(function (el) {
                observer.observe(el);
            });
        } else {
            items.forEach(function (el) {
                el.classList.add('od19-pc-in');
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
