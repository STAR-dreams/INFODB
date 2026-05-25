$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="popover"]').popover();

    $('.dropdown-toggle').dropdown();

    // 初始化子菜单指示器
    $('.has-submenu').each(function() {
        if ($(this).next('.collapse').hasClass('show')) {
            $(this).find('.submenu-indicator').removeClass('fa-chevron-right').addClass('fa-chevron-down');
        }
    });

    $('.has-submenu').on('click', function(e) {
        if ($(window).width() < 992) {
            e.preventDefault();
            $(this).next('.collapse').toggleClass('show');
            $(this).parent().toggleClass('active');
            $(this).find('.submenu-indicator').toggleClass('fa-chevron-down fa-chevron-right');
        }
    });

    $('#sidebarToggle').on('click', function() {
        $('.sidebar').toggleClass('show');
    });

    $('form').on('submit', function(e) {
        var requiredFields = $(this).find('[required]');
        var isValid = true;

        requiredFields.each(function() {
            if (!$(this).val().trim()) {
                isValid = false;
                $(this).addClass('is-invalid');
                $(this).next('.invalid-feedback').remove();
                $(this).after('<div class="invalid-feedback">此字段为必填项</div>');
            } else {
                $(this).removeClass('is-invalid');
                $(this).next('.invalid-feedback').remove();
            }
        });

        if (!isValid) {
            e.preventDefault();
            var firstInvalid = $(this).find('.is-invalid').first();
            if (firstInvalid.length) {
                $('html, body').animate({
                    scrollTop: firstInvalid.offset().top - 100
                }, 300);
            }
        }
    });

    $('form input[required], form select[required], form textarea[required]').on('blur change', function() {
        if ($(this).val().trim()) {
            $(this).removeClass('is-invalid');
            $(this).next('.invalid-feedback').remove();
        }
    });

    $('.form-control').on('focus', function() {
        $(this).closest('.form-group').addClass('focused');
    }).on('blur', function() {
        $(this).closest('.form-group').removeClass('focused');
    });

    if ($('#dataTable').length) {
        initializeDataTable();
    }

    if ($('#searchForm').length) {
        initializeSearchForm();
    }

    if ($('#confirmModal').length) {
        initializeConfirmModal();
    }

    $('.btn-delete').on('click', function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        var title = $(this).data('title') || '此记录';

        $('#confirmModal .modal-title').text('确认删除');
        $('#confirmModal .modal-body').html('<p>确定要删除 <strong>' + title + '</strong> 吗？此操作不可撤销。</p>');
        $('#confirmModal #confirmBtn').attr('href', url).text('确认删除');
        $('#confirmModal').modal('show');
    });

    $('.btn-action').on('click', function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        var title = $(this).data('title') || '此操作';
        var action = $(this).data('action') || '执行';

        $('#confirmModal .modal-title').text('确认' + action);
        $('#confirmModal .modal-body').html('<p>确定要' + action + ' <strong>' + title + '</strong> 吗？</p>');
        $('#confirmModal #confirmBtn').attr('href', url).text('确认' + action);
        $('#confirmModal').modal('show');
    });

    $('.table-responsive').on('scroll', function() {
        var scrollLeft = $(this).scrollLeft();
        $('.sticky-left').css('left', scrollLeft);
    });

    $('input[type="number"]').on('input', function() {
        var value = $(this).val();
        var min = parseFloat($(this).attr('min'));
        var max = parseFloat($(this).attr('max'));

        if (min !== undefined && value < min) {
            $(this).val(min);
        }
        if (max !== undefined && value > max) {
            $(this).val(max);
        }
    });

    $('#exportBtn').on('click', function(e) {
        e.preventDefault();
        var format = $(this).data('format') || 'csv';
        var table = $(this).data('table');

        var form = $('<form>', {
            method: 'POST',
            action: '/export/' + table + '/' + format
        });
        $('body').append(form);
        form.submit();
        form.remove();
    });

    $('[data-copy]').on('click', function() {
        var target = $($(this).data('copy'));
        target.select();
        document.execCommand('copy');

        $(this).tooltip('hide')
            .attr('data-original-title', '已复制！')
            .tooltip('show')
            .one('hidden.bs.tooltip', function() {
                $(this).attr('data-original-title', '点击复制');
            })
            .tooltip('setContent', { 'title': '已复制！' });
    });

    $('.lazy-load').Lazy({
        effect: 'fadeIn',
        effectTime: 300,
        threshold: 0
    });

    if (typeof initMap === 'function') {
        initMap();
    }

    autoHideAlerts();
});

function initializeDataTable() {
    var table = $('#dataTable');
    var pagination = $('#pagination');
    var rowsPerPage = 10;
    var currentPage = 1;
    var allRows = table.find('tbody tr');
    var totalRows = allRows.length;

    function renderPagination() {
        var totalPages = Math.ceil(totalRows / rowsPerPage);
        var html = '';

        if (totalPages > 1) {
            html += '<nav aria-label="分页">';
            html += '<ul class="pagination">';

            html += '<li class="page-item' + (currentPage === 1 ? ' disabled' : '') + '">';
            html += '<a class="page-link" href="#" data-page="' + (currentPage - 1) + '" aria-label="上一页">';
            html += '<span aria-hidden="true">&laquo;</span>';
            html += '</a></li>';

            for (var i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                    html += '<li class="page-item' + (i === currentPage ? ' active' : '') + '">';
                    html += '<a class="page-link" href="#" data-page="' + i + '">' + i + '</a></li>';
                } else if (i === currentPage - 3 || i === currentPage + 3) {
                    html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
                }
            }

            html += '<li class="page-item' + (currentPage === totalPages ? ' disabled' : '') + '">';
            html += '<a class="page-link" href="#" data-page="' + (currentPage + 1) + '" aria-label="下一页">';
            html += '<span aria-hidden="true">&raquo;</span>';
            html += '</a></li>';

            html += '</ul></nav>';
        }

        pagination.html(html);
    }

    function renderTable() {
        allRows.hide();
        var start = (currentPage - 1) * rowsPerPage;
        var end = start + rowsPerPage;

        allRows.slice(start, end).show();

        var showingInfo = '显示 ' + (start + 1) + '-' + Math.min(end, totalRows) + ' 条，共 ' + totalRows + ' 条';
        $('#tableInfo').text(showingInfo);
    }

    table.on('click', '.page-link', function(e) {
        e.preventDefault();
        var page = parseInt($(this).data('page'));
        if (page && page !== currentPage && page > 0 && page <= Math.ceil(totalRows / rowsPerPage)) {
            currentPage = page;
            renderTable();
            renderPagination();

            $('html, body').animate({
                scrollTop: table.offset().top - 100
            }, 300);
        }
    });

    $('#rowsPerPage').on('change', function() {
        rowsPerPage = parseInt($(this).value);
        currentPage = 1;
        renderTable();
        renderPagination();
    });

    renderTable();
    renderPagination();
}

function initializeSearchForm() {
    var searchForm = $('#searchForm');
    var searchInput = $('#searchInput');
    var searchColumn = $('#searchColumn');
    var searchButton = $('#searchButton');
    var resetButton = $('#resetButton');
    var table = $('#dataTable');

    searchButton.on('click', function() {
        performSearch();
    });

    searchInput.on('keypress', function(e) {
        if (e.which === 13) {
            performSearch();
        }
    });

    resetButton.on('click', function() {
        searchInput.val('');
        searchColumn.val('');
        table.find('tbody tr').show();
        $('#searchResults').remove();
        var info = table.find('tbody tr').length + ' 条记录';
        $('#tableInfo').text(info);
    });

    function performSearch() {
        var keyword = searchInput.val().trim().toLowerCase();
        var column = searchColumn.val();

        if (!keyword) {
            alert('请输入搜索关键词');
            return;
        }

        var rows = table.find('tbody tr');
        var matchedCount = 0;

        rows.hide();

        rows.each(function() {
            var cell = column ? $(this).find('td:eq(' + column + ')') : $(this).find('td');
            var text = cell.text().toLowerCase();

            if (text.indexOf(keyword) !== -1) {
                $(this).show();
                matchedCount++;
            }
        });

        if (matchedCount === 0) {
            table.after('<div id="searchResults" class="alert alert-warning">未找到匹配的结果</div>');
        } else {
            table.after('<div id="searchResults" class="alert alert-success">找到 ' + matchedCount + ' 条匹配结果</div>');
        }

        setTimeout(function() {
            $('#searchResults').fadeOut(function() {
                $(this).remove();
            });
        }, 3000);
    }
}

function initializeConfirmModal() {
    $('#confirmBtn').on('click', function() {
        var href = $(this).attr('href');
        if (href) {
            window.location.href = href;
        }
    });
}

function autoHideAlerts() {
    $('.alert').each(function() {
        var alert = $(this);
        var delay = alert.data('delay') || 5000;

        setTimeout(function() {
            alert.fadeOut(function() {
                $(this).remove();
            });
        }, delay);
    });
}

function showLoading(element) {
    element.html('<div class="text-center py-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-2">加载中...</p></div>');
}

function hideLoading(element) {
    element.find('.fa-spinner').closest('.text-center').remove();
}

function showToast(message, type) {
    var toastClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-info');
    var toast = $('<div class="toast ' + toastClass + '" role="alert" aria-live="assertive" aria-atomic="true">');
    toast.html('<div class="toast-header text-white ' + toastClass + '"><strong class="mr-auto">提示</strong><button type="button" class="ml-2 mb-1 close" data-dismiss="toast">&times;</button></div>');
    toast.append('<div class="toast-body text-white">' + message + '</div>');

    $('#toastContainer').append(toast);
    toast.toast({ delay: 3000 });
    toast.toast('show');

    toast.on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

function formatCoordinate(lat, lng) {
    var latDir = lat >= 0 ? 'N' : 'S';
    var lngDir = lng >= 0 ? 'E' : 'W';
    return Math.abs(lat).toFixed(4) + '° ' + latDir + ', ' + Math.abs(lng).toFixed(4) + '° ' + lngDir;
}

function formatDistance(km) {
    if (km >= 1000) {
        return (km / 1000).toFixed(2) + ' km';
    }
    return km.toFixed(2) + ' km';
}

function formatFrequency(mhz) {
    return parseFloat(mhz).toFixed(3) + ' MHz';
}

function debounce(func, wait) {
    var timeout;
    return function() {
        var context = this;
        var args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() {
            func.apply(context, args);
        }, wait);
    };
}

function serializeForm(form) {
    var data = {};
    var array = form.serializeArray();
    $.each(array, function() {
        if (data[this.name]) {
            if (!data[this.name].push) {
                data[this.name] = [data[this.name]];
            }
            data[this.name].push(this.value || '');
        } else {
            data[this.name] = this.value || '';
        }
    });
    return data;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    var date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function truncateText(text, maxLength) {
    if (!text) return '-';
    text = String(text);
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}
