import re
import sys

filepath = r'd:\ITMS\frontend\src\app\features\training\training-management.component.ts'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# find template
template_pattern = re.compile(r'template:\s*`([^`]+)`\s*,')
m_template = template_pattern.search(content)
if not m_template:
    print("Could not find template")
    sys.exit(1)

html_content = m_template.group(1).strip('\n\r')

# write html
with open(r'd:\ITMS\frontend\src\app\features\training\training-management.component.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# replace in content
content = content[:m_template.start()] + "templateUrl: './training-management.component.html'," + content[m_template.end():]

# find styles
styles_pattern = re.compile(r'styles:\s*\[\s*`([^`]+)`\s*,\s*\]\s*,')
m_styles = styles_pattern.search(content)

if not m_styles:
    styles_pattern2 = re.compile(r'styles:\s*\[\s*`([^`]+)`\s*\]\s*,')
    m_styles = styles_pattern2.search(content)

if not m_styles:
    print("Could not find styles")
    sys.exit(1)

scss_content = m_styles.group(1).strip('\n\r')

# write scss
with open(r'd:\ITMS\frontend\src\app\features\training\training-management.component.scss', 'w', encoding='utf-8') as f:
    f.write(scss_content)

# replace in content
content = content[:m_styles.start()] + "styleUrl: './training-management.component.scss'," + content[m_styles.end():]

# write TS
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Success")
