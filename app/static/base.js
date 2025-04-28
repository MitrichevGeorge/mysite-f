document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.close').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
            const tabName = this.previousElementSibling.textContent;
            removeTab(tabName);
        });
    });

    function removeTab(tabName) {
        const tabs = document.querySelectorAll('.tab');
        let tabIndex = -1;
    
        tabs.forEach((tab, index) => {
            if (tab.textContent.includes(tabName)) {
                tabIndex = index;
            }
        });
    
        if (tabIndex !== -1) {
            fetch(`/api/del_tab/${tabIndex}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const tabToRemove = tabs[tabIndex];
                tabToRemove.remove();
                console.log('Updated tabs:', data);
            })
            .catch(error => {
                console.error('Error removing tab:', error);
            });
        }
    }

    const homeArrow = document.getElementById('home-arrow');
    const homeDropdown = document.getElementById('home-dropdown');

    if (homeArrow && homeDropdown) {
        homeArrow.addEventListener('click', function() {
            const isOpen = homeDropdown.style.display === 'block';
            homeDropdown.style.display = isOpen ? 'none' : 'block';
            homeArrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
            homeDropdown.style.left = '0px';
            homeDropdown.style.top = `${homeArrow.offsetTop + homeArrow.offsetHeight + 10}px`;
        });

        homeArrow.addEventListener('mouseleave', function() {
            setTimeout(() => {
                if (!homeDropdown.matches(':hover')) {
                    homeDropdown.style.display = 'none';
                    homeArrow.style.transform = 'rotate(0deg)';
                }
            }, 100);
        });

        homeDropdown.addEventListener('mouseleave', function() {
            homeDropdown.style.display = 'none';
            homeArrow.style.transform = 'rotate(0deg)';
        });
    }

    const scrollContainer = document.getElementById('tabs');
    const noScrollElements = document.querySelectorAll('#noscroll');
    scrollContainer.addEventListener('scroll', () => {
        const { scrollLeft, scrollWidth, clientWidth } = scrollContainer;
        const isAtStart = scrollLeft === 0;
        const isAtEnd = Math.ceil(scrollLeft + clientWidth) >= scrollWidth;

        if (isAtStart) {
            scrollContainer.classList.remove('show-left-shadow');
        } else {
            scrollContainer.classList.add('show-left-shadow');
        }

        if (isAtEnd) {
            scrollContainer.classList.remove('show-right-shadow');
        } else {
            scrollContainer.classList.add('show-right-shadow');
        }
        noScrollElements.forEach((element) => {
            const rect = element.getBoundingClientRect();
            const containerRect = scrollContainer.getBoundingClientRect();
            
            element.style.transform = `translateX(${scrollContainer.scrollLeft}px)`;
            element.style.top = `${rect.top - containerRect.top}px`;
        });
    });

    const userName = document.getElementById('user-name');
    const userDropdown = document.getElementById('user-dropdown');

    if (userName && userDropdown) {
        userName.addEventListener('click', function() {
            userDropdown.style.display = userDropdown.style.display === 'none' ? 'block' : 'none';
            userDropdown.style.left = `${userName.offsetLeft-100}px`;
            userDropdown.style.top = `${userName.offsetTop + userName.offsetHeight}px`;
        });

        userName.addEventListener('mouseleave', function() {
            setTimeout(() => {
                if (!userDropdown.matches(':hover')) {
                    userDropdown.style.display = 'none';
                }
            }, 100);
        });

        userDropdown.addEventListener('mouseleave', function() {
            userDropdown.style.display = 'none';
        });
    }
});