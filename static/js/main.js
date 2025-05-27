(function ($) {
    "use strict";

    // Spinner - Hide loading spinner after page loads
    var spinner = function () {
        setTimeout(function () {
            if ($('#spinner').length > 0) {
                $('#spinner').removeClass('show');
            }
        }, 1);
    };
    spinner();

    // Sidebar Toggler - Essential for your dashboard navigation
    $('.sidebar-toggler').click(function () {
        $('.sidebar, .content').toggleClass("open");
        return false;
    });

    // Smooth scrolling for navigation links (useful for your home page)
    $(document).on('click', 'a[href^="#"]', function(event) {
        event.preventDefault();
        
        var target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 80 // Account for fixed navbar
            }, 1000);
        }
    });

    // Simple fade-in animation for cards when they come into view
    function checkVisibility() {
        $('.card, .feature-card').each(function() {
            var element = $(this);
            var elementTop = element.offset().top;
            var elementBottom = elementTop + element.outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();
            
            // If element is in viewport, add visible class
            if (elementBottom > viewportTop && elementTop < viewportBottom - 100) {
                element.addClass('fade-in-visible');
            }
        });
    }

    // Run visibility check on scroll and load
    $(window).on('scroll', checkVisibility);
    $(document).ready(checkVisibility);

    // Progress Bar Animation - Simple version without waypoints
    function animateProgressBars() {
        $('.progress .progress-bar').each(function() {
            var progressBar = $(this);
            var percentage = progressBar.attr('aria-valuenow');
            
            // Only animate if not already animated
            if (!progressBar.hasClass('animated')) {
                progressBar.addClass('animated');
                progressBar.css('width', '0%').animate({
                    width: percentage + '%'
                }, 1500);
            }
        });
    }

    // Trigger progress bars when they're visible
    $(window).on('scroll', function() {
        $('.pg-bar').each(function() {
            var element = $(this);
            var elementTop = element.offset().top;
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();
            
            if (elementTop < viewportBottom - 100) {
                animateProgressBars();
            }
        });
    });

    // Initialize everything when document is ready
    $(document).ready(function() {
        // Trigger initial animations
        checkVisibility();
        
        // If there are progress bars visible on load, animate them
        if ($('.pg-bar').length > 0) {
            setTimeout(animateProgressBars, 500);
        }
    });

    // Night mode compatibility - Listen for night mode changes
    $(document).on('nightModeToggled', function() {
        // Any additional JavaScript needed when night mode toggles
        console.log('Night mode toggled');
    });

})(jQuery);