(function () {
    "use strict";

    function getJQuery() {
        return window.jQuery || (window.django && window.django.jQuery) || null;
    }

    function fetchBranches(url, companyId) {
        if (!url || !companyId) {
            return Promise.resolve([]);
        }

        return fetch(url + "?company=" + encodeURIComponent(companyId), {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        })
            .then(function (response) {
                if (!response.ok) {
                    return { results: [] };
                }
                return response.json();
            })
            .then(function (data) {
                return data.results || [];
            })
            .catch(function () {
                return [];
            });
    }

    function refreshSelect2($, $select) {
        if (!$select.length || typeof $select.select2 !== "function") {
            return;
        }

        if ($select.hasClass("select2-hidden-accessible")) {
            $select.select2("destroy");
        }

        var width = $select.hasClass("search-filter") ? "100%" : "element";
        $select.select2({ width: width, minimumInputLength: 0 });
    }

    function bindFormDependentSelect($) {
        var $company = $("#id_company");
        var $branch = $("#id_company_branch");

        if (!$company.length || !$branch.length) {
            return;
        }

        var branchesUrl = $branch.data("branches-url") || $branch.attr("data-branches-url");
        var requestId = 0;

        function populateFormBranches(companyId, selectedId) {
            var currentRequest = ++requestId;
            var previousValue = selectedId != null ? selectedId : $branch.val();

            $branch.find("option:not(:first)").remove();

            if (!companyId) {
                $branch.val("");
                refreshSelect2($, $branch);
                return;
            }

            fetchBranches(branchesUrl, companyId).then(function (branches) {
                if (currentRequest !== requestId) {
                    return;
                }

                branches.forEach(function (branch) {
                    var isSelected = String(branch.id) === String(previousValue);
                    $branch.append(new Option(branch.name, branch.id, false, isSelected));
                });

                if (
                    previousValue &&
                    $branch.find('option[value="' + previousValue + '"]').length
                ) {
                    $branch.val(previousValue);
                } else {
                    $branch.val("");
                }

                refreshSelect2($, $branch);
            });
        }

        $company.on("change", function () {
            populateFormBranches($company.val());
        });

        if ($company.val() && $branch.find("option").length <= 1) {
            populateFormBranches($company.val(), $branch.val());
        }
    }

    function bindChangelistDependentFilter($) {
        var $companyFilter = $('.search-filter[data-name="company"]');
        var $branchFilter = $(
            '.search-filter[data-parent-filter="company"], .search-filter[data-name="company_branch"]'
        ).first();

        if (!$companyFilter.length || !$branchFilter.length) {
            return;
        }

        var branchesUrl =
            $branchFilter.data("branches-url") || $branchFilter.attr("data-branches-url");
        var lookupKwarg =
            $branchFilter.data("lookup") ||
            $branchFilter.attr("data-lookup") ||
            "company_branch__id__exact";
        var requestId = 0;

        function populateFilterBranches(companyId, selectedId) {
            var currentRequest = ++requestId;
            var previousValue = selectedId != null ? selectedId : $branchFilter.val();

            $branchFilter.find("option[data-name]").remove();

            if (!companyId) {
                $branchFilter.removeAttr("name");
                refreshSelect2($, $branchFilter);
                return;
            }

            fetchBranches(branchesUrl, companyId).then(function (branches) {
                if (currentRequest !== requestId) {
                    return;
                }

                branches.forEach(function (branch) {
                    var $option = $("<option></option>")
                        .attr("value", branch.id)
                        .attr("data-name", lookupKwarg)
                        .text(branch.name);

                    if (String(branch.id) === String(previousValue)) {
                        $option.prop("selected", true);
                    }

                    $branchFilter.append($option);
                });

                if (
                    previousValue &&
                    $branchFilter.find('option[value="' + previousValue + '"]').length
                ) {
                    $branchFilter.val(previousValue);
                    $branchFilter.attr("name", lookupKwarg);
                } else {
                    $branchFilter.val("");
                    $branchFilter.removeAttr("name");
                }

                refreshSelect2($, $branchFilter);
            });
        }

        $companyFilter.on("change", function () {
            populateFilterBranches($companyFilter.val());
        });

        if ($companyFilter.val()) {
            populateFilterBranches($companyFilter.val(), $branchFilter.val());
        }
    }

    function start() {
        var $ = getJQuery();
        if (!$) {
            return;
        }

        bindFormDependentSelect($);
        bindChangelistDependentFilter($);
    }

    if (document.readyState === "complete") {
        start();
    } else {
        window.addEventListener("load", start);
    }
})();
