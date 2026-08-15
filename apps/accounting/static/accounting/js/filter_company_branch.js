(function () {
  function getJQuery() {
    if (window.django && django.jQuery) {
      return django.jQuery;
    }
    return window.jQuery;
  }

  function init($) {
    var $company = $("#id_company");
    var $branch = $("#id_company_branch");
    if (!$company.length || !$branch.length) {
      return;
    }

    var url = $branch.data("branches-url");
    if (!url) {
      return;
    }

    function loadBranches(companyId, selectedId) {
      $branch.find("option:not([value=''])").remove();
      if (!companyId) {
        $branch.val("").trigger("change");
        return;
      }

      $.getJSON(url, { company: companyId }, function (data) {
        $.each(data.results || [], function (_, item) {
          var isSelected = String(item.id) === String(selectedId);
          $branch.append(new Option(item.name, item.id, isSelected, isSelected));
        });
        $branch.trigger("change");
      });
    }

    $company.on("change", function () {
      loadBranches($(this).val(), null);
    });
  }

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    var $ = getJQuery();
    if ($) {
      init($);
    }
  });
})();
