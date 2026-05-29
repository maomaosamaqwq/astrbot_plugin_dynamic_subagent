# 🐾 Dynamic SubAgent — العربية

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

إضافة AstrBot تتيح للوكيل الرئيسي إنشاء وإدارة الوكلاء الفرعيين بشكل ديناميكي، مع **عزل الأذونات** و**تحديد عمق التداخل** لنظام وكلاء متعدد آمن.

## ✨ الميزات

| الميزة | الوصف |
|--------|-------|
| 🧠 إنشاء ديناميكي | `spawn_agent` ينشئ وكلاء فرعيين عند الطلب مع أذونات/نماذج/استمرارية قابلة للتكوين |
| 🔄 نقل المهام | `transfer_to_agent` يوكل المهام للوكلاء الفرعيين الموجودين |
| 🔒 عزل الأذونات | ثلاث مستويات: `safe` / `medium` / `full` — الوكلاء الفرعيون لا يستطيعون التصعيد |
| 🛡 تحديد العمق | الوكلاء الفرعيون لا يستطيعون إنشاء وكلاء فرعيين آخرين، منع السلاسل اللانهائية |
| 💾 ذاكرة مستمرة | الوكلاء المستمرون يحتفظون بالسياق بعد إعادة التشغيل + حقن السجل |
| 🕥 تتبع التعاون | تتبع كامل لسلاسل spawn/transfer وتقارير |

## 📦 التثبيت

ابحث عن `dynamic_subagent` في AstrBot Plugin Marketplace، أو استنساخ يدوي:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 البدء السريع

```python
# 1. إنشاء وكيل فرعي بمهمة فورية
spawn_agent(
    name="code_reviewer",
    description="مساعد مراجعة الكود",
    permission_level="medium",
    task="يرجى مراجعة الكود التالي: ..."
)

# 2. إنشاء وكيل فرعي مستمر للنقل اللاحق
spawn_agent(
    name="memory_bot",
    description="مساعد ذاكرة يتذكر المحادثات",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="نواصل موضوعنا السابق..."
)

# 3. عرض تقرير التعاون
show_collaboration_report()
```

## 📝 الرخصة

MIT

---
*هذه المقدمة مكتوبة باللغة العربية.*
