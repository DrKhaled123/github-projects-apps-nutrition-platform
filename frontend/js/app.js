(function(){
  // Add error handling for failed resource loads
  window.addEventListener('error', function(e) {
    console.error('Resource failed to load:', e.target.src || e.target.href);
  });

  window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
  });

  // Add loading states
  document.addEventListener('DOMContentLoaded', function() {
    // Remove any loading spinners
    const loaders = document.querySelectorAll('.loading');
    loaders.forEach(loader => loader.style.display = 'none');
  });

  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  const strings = {
    en: {
      home: 'Home', diet: 'Diet & Meals', workouts: 'Workouts', lifestyle: 'Lifestyle', recipes: 'Recipes',
      heroTitle: 'Your Personalized Health Companion',
      heroSubtitle: 'Evidence-based plans for nutrition, workouts, lifestyle and recipes.',
      dietDesc: 'Weekly personalized plans with ingredients, methods, and nutrition.',
      workoutsDesc: 'Smart routines, injury guidance, sets/reps, warmups, and supplements.',
      lifestyleDesc: 'Condition-based guidance, nutrition, habits, and treatment suggestions.',
      recipesDesc: 'Cuisine preferences, dislikes, tips and alternatives. Free plan: 3 gens.',
      ctaTitle: 'Take the Pro account and be a special member',
      ctaButton: 'Subscribe now',
      quotesTitle: 'Real quotes about healthy living',
      storiesTitle: 'Real stories of commitment',
      storiesBody: 'People who consistently follow simple, evidence-based routines often report better energy, weight balance, and mood. Your journey can start today.',
      contactTitle: 'Contact', phone: 'Phone', businessEmail: 'Business', personalEmail: 'Personal',
      becomePro: 'Become Pro'
    },
    ar: {
      home: 'الرئيسية', diet: 'النظام الغذائي', workouts: 'التمارين', lifestyle: 'نمط الحياة', recipes: 'الوصفات',
      heroTitle: 'رفيقك الشخصي للصحة',
      heroSubtitle: 'خطط مبنية على الأدلة للتغذية والتمارين ونمط الحياة والوصفات.',
      dietDesc: 'خطط أسبوعية مخصصة مع المكونات وطريقة التحضير والقيم الغذائية.',
      workoutsDesc: 'جداول ذكية، إرشادات الإصابات، العدّات والمجموعات، الإحماء والمكملات.',
      lifestyleDesc: 'إرشادات حسب الحالة، التغذية والعادات وخطط علاجية مقترحة.',
      recipesDesc: 'تفضيلات المطبخ والكراهات، نصائح وبدائل. الخطة المجانية: 3 مرات.',
      ctaTitle: 'احصل على حساب برو وكن عضواً مميزاً',
      ctaButton: 'اشترك الآن',
      quotesTitle: 'اقتباسات حقيقية عن الحياة الصحية',
      storiesTitle: 'قصص حقيقية عن الالتزام',
      storiesBody: 'من يلتزم بعادات بسيطة مبنية على الأدلة غالباً ما يشعر بطاقة ومزاج أفضل وتوازن بالوزن. ابدأ اليوم.',
      contactTitle: 'تواصل', phone: 'هاتف', businessEmail: 'الأعمال', personalEmail: 'شخصي',
      becomePro: 'انضم للبرو'
    }
  };

  let lang = localStorage.getItem('lang') || 'en';
  function applyLang(l){
    document.documentElement.setAttribute('lang', l);
    document.documentElement.setAttribute('dir', l === 'ar' ? 'rtl' : 'ltr');
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (strings[l][key]) el.textContent = strings[l][key];
    });
    const toggle = document.getElementById('langToggle');
    if (toggle) toggle.textContent = l === 'ar' ? 'English' : 'العربية';
    localStorage.setItem('lang', l);
  }
  applyLang(lang);

  const toggle = document.getElementById('langToggle');
  if (toggle) toggle.addEventListener('click', () => {
    lang = (lang === 'en') ? 'ar' : 'en';
    applyLang(lang);
  });

  // Plan badge from cookies
  function getCookie(name){
    return document.cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith(name+'='))?.split('=')[1] || '';
  }
  const planBadge = document.getElementById('planBadge');
  if (planBadge) {
    const plan = getCookie('plan') || 'free';
    planBadge.textContent = plan.charAt(0).toUpperCase() + plan.slice(1);
  }
})();


