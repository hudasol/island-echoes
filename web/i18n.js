/* Interface strings for Island Echoes. Only interface text is translated. Facts, citations, creature
   names and source titles stay in the language of the source, and nothing here is machine translated
   at run time. English is the fallback for any missing key. */
(() => {
  "use strict";
  const EN = {
    skip: "Skip to the field agent", nav_islands: "Islands", gibs: "NASA GIBS imagery",
    tagline: "Seven remote islands. One creature on each, speaking only from sources.",
    layer_h: "Satellite layer", about_btn: "About the data and credits",
    globe_hint: "Drag to turn the globe. Choose an island to fly there.",
    field_agent: "Field agent", sites_h: "Field sites",
    lede: "Seven islands, eight creatures. Select a row, a pin or an island in the list.",
    th_site: "Site", th_creature: "Creature", th_status: "Status", th_facts: "Facts", total: "Total",
    dt_library: "Library", dd_library: "Every entry carries its source, publisher and retrieval date. A search the sources cannot answer returns nothing.",
    dt_climate: "Climate", dd_climate: "NASA POWER 2001 to 2020 monthly means for the grid cell around each island.",
    dt_species: "Species", dd_species: "GBIF records and the IUCN Red List category GBIF holds for each creature.",
    ops_link: "Operations and evaluation", api_link: "API reference",
    sheet_handle: "Expand or collapse the field agent panel", pin_summary: "About this pin",
    educator: "Educator sheet", close: "Close", tab_agent: "Field agent", tab_library: "Library",
    pause: "Pause motion", play: "Play motion", climate_h: "Climate readings",
    cell_note: "Each value describes a NASA POWER grid cell about 55 km by 70 km, which is larger than the island, so it blends land and open sea. It describes the area, not a station on the shore.",
    report_h: "Field report", read_aloud: "Read aloud", stop: "Stop",
    learn_h: "Learn facts from the library", your_question: "Your question", search: "Search",
    ask_ph: "Ask about climate, water, species or history",
    ask_note: "Answers come only from the library's sourced entries. If the library has nothing on your question, it says so.",
    browse: "Browse the whole library", ask_creature: "Ask the creature", ask: "Ask",
    chat_ph: "Ask about climate, history, or the species",
    chat_note: "Answers use only the sources shown. If the sources are silent, the creature says so.",
    usage: "Usage statistics", lib_h: "Island library",
    lib_intro: "Every entry is a sourced fact. Search by topic, or filter by category.",
    lib_label: "Search this island's library", lib_ph: "Try: coral bleaching, rainfall, endangered birds",
    update: "A new version of Island Echoes is ready.", reload: "Reload",
    tuning: "Tuning in…", searching: "Searching…", reading: "Reading NASA POWER…",
    no_webgl: "The 3D globe needs WebGL, which this browser has not enabled. The island list and field agent still work.",
    sensor_fail: "Sensor readings are unavailable right now.",
    report_fail: "The field report could not be loaded.",
    lib_fail: "The library could not be loaded.",
    server_fail: "Could not reach the Island Echoes server.",
    entry_one: "entry", entry_many: "entries",
    switch_label: "Switch language to English", switch_text: "English",
  };
  const AR = {
    skip: "انتقل إلى المرشد الميداني", nav_islands: "الجزر", gibs: "صور ناسا GIBS",
    tagline: "سبع جزر نائية. كائن واحد على كل جزيرة، لا يتحدث إلا من المصادر.",
    layer_h: "طبقة الأقمار الصناعية", about_btn: "حول البيانات والمصادر",
    globe_hint: "اسحب لتدوير الكرة الأرضية. اختر جزيرة للانتقال إليها.",
    field_agent: "المرشد الميداني", sites_h: "المواقع الميدانية",
    lede: "سبع جزر وثمانية كائنات. اختر صفاً أو دبوساً أو جزيرة من القائمة.",
    th_site: "الموقع", th_creature: "الكائن", th_status: "الحالة", th_facts: "الحقائق", total: "المجموع",
    dt_library: "المكتبة", dd_library: "كل مدخل يحمل مصدره وناشره وتاريخ استرجاعه. إذا لم تستطع المصادر الإجابة عن سؤال فلا تُعاد أي نتيجة.",
    dt_climate: "المناخ", dd_climate: "متوسطات شهرية من ناسا POWER للفترة من 2001 إلى 2020 لخلية الشبكة المحيطة بكل جزيرة.",
    dt_species: "الأنواع", dd_species: "سجلات GBIF وفئة القائمة الحمراء للاتحاد الدولي لحفظ الطبيعة التي يحتفظ بها GBIF لكل كائن.",
    ops_link: "التشغيل والتقييم", api_link: "مرجع واجهة البرمجة",
    sheet_handle: "توسيع لوحة المرشد الميداني أو طيّها", pin_summary: "حول هذا الدبوس",
    educator: "ورقة المعلم", close: "إغلاق", tab_agent: "المرشد الميداني", tab_library: "المكتبة",
    pause: "إيقاف الحركة", play: "تشغيل الحركة", climate_h: "قراءات المناخ",
    cell_note: "تصف كل قيمة خلية شبكة من ناسا POWER مساحتها نحو 55 كم في 70 كم، وهي أكبر من الجزيرة، فتجمع بين اليابسة والبحر المفتوح. إنها تصف المنطقة وليس محطة على الشاطئ.",
    report_h: "التقرير الميداني", read_aloud: "قراءة بصوت عال", stop: "إيقاف",
    learn_h: "تعلّم حقائق من المكتبة", your_question: "سؤالك", search: "بحث",
    ask_ph: "اسأل عن المناخ أو الماء أو الأنواع أو التاريخ",
    ask_note: "تأتي الإجابات من مدخلات المكتبة الموثقة فقط. إذا لم تجد المكتبة شيئاً عن سؤالك فإنها تقول ذلك.",
    browse: "تصفح المكتبة كاملة", ask_creature: "اسأل الكائن", ask: "اسأل",
    chat_ph: "اسأل عن المناخ أو التاريخ أو النوع",
    chat_note: "تستخدم الإجابات المصادر المعروضة فقط. إذا سكتت المصادر فإن الكائن يقول ذلك.",
    usage: "إحصاءات الاستخدام", lib_h: "مكتبة الجزيرة",
    lib_intro: "كل مدخل حقيقة موثقة. ابحث بالموضوع أو صفّ حسب الفئة.",
    lib_label: "ابحث في مكتبة هذه الجزيرة", lib_ph: "جرّب: ابيضاض المرجان، هطول الأمطار، الطيور المهددة",
    update: "يتوفر إصدار جديد من Island Echoes.", reload: "إعادة التحميل",
    tuning: "جارٍ الاستماع…", searching: "جارٍ البحث…", reading: "جارٍ قراءة بيانات ناسا POWER…",
    no_webgl: "تحتاج الكرة الأرضية ثلاثية الأبعاد إلى WebGL ولم يفعّله هذا المتصفح. تبقى قائمة الجزر والمرشد الميداني تعملان.",
    sensor_fail: "قراءات المستشعرات غير متاحة حالياً.",
    report_fail: "تعذر تحميل التقرير الميداني.",
    lib_fail: "تعذر تحميل المكتبة.",
    server_fail: "تعذر الوصول إلى خادم Island Echoes.",
    entry_one: "مدخل", entry_many: "مدخلات",
    switch_label: "تغيير اللغة إلى الإنجليزية", switch_text: "English",
  };
  const TABLES = { en: EN, ar: AR };
  let lang = "en";
  try { const s = localStorage.getItem("ie-lang"); if (s === "ar" || s === "en") lang = s; } catch (_) { /* storage may be blocked */ }

  function t(key, fallback) { return (TABLES[lang] && TABLES[lang][key]) || EN[key] || fallback || key; }

  function apply() {
    const root = document.documentElement;
    root.lang = lang; root.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    document.querySelectorAll("[data-i18n-aria]").forEach((n) => n.setAttribute("aria-label", t(n.dataset.i18nAria)));
    document.querySelectorAll("[data-i18n-ph]").forEach((n) => n.setAttribute("placeholder", t(n.dataset.i18nPh)));
    const b = document.getElementById("lang-toggle");
    if (b) {
      b.textContent = lang === "ar" ? EN.switch_text : "العربية";
      b.lang = lang === "ar" ? "en" : "ar";
      b.setAttribute("aria-label", lang === "ar" ? EN.switch_label : "Switch language to Arabic");
      if (lang === "ar") b.setAttribute("aria-label", AR.switch_label);
    }
    document.dispatchEvent(new CustomEvent("ie-lang", { detail: { lang } }));
  }
  function set(next) {
    if (!TABLES[next]) return;
    lang = next;
    try { localStorage.setItem("ie-lang", lang); } catch (_) { /* ignore */ }
    apply();
  }
  window.I18N = { t, set, get lang() { return lang; }, tables: TABLES };
  document.addEventListener("DOMContentLoaded", () => {
    const b = document.getElementById("lang-toggle");
    if (b) b.addEventListener("click", () => set(lang === "ar" ? "en" : "ar"));
    apply();
  });
})();
