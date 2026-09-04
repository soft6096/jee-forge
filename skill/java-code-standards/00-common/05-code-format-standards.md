# 代码格式规范 (Code Format Standards)

## 适用范围

生成任意 Java 代码前必读。规范缩进、换行、空行、导入、常见语法陷阱。实际格式化以团队 IDE 配置（.editorconfig / Checkstyle / Spotless）为准，本文档为生成代码时的基准。

## 强制规则

### 1. 基础格式

- 缩进：4 空格，禁止 Tab（IDE 配置展开 Tab）
- 行宽：120 字符以内（团队配置为准）
- 编码：UTF-8，换行符 LF
- 文件结尾保留一个空行

### 2. 空行规则

- 方法之间空 1 行
- 逻辑分组之间空 1 行（声明区 / 处理区 / 返回区）
- 类内字段与方法之间空 1 行
- ❌ 连续 2 行以上空行
- ❌ 方法体内首行缩进后紧跟空行

### 3. 导入顺序

按分组，组间空 1 行：

```java
import static com.example.Constants.MAX_PAGE_SIZE;  // 1. static

import com.example.common.Response;                    // 2. 第三方与自身
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
```

- 顺序：static → 自身项目 → 第三方（按字母序）
- ❌ 通配符导入：`import java.util.*;`（IDE 自动展开）
- ❌ **禁止未使用 import**：每个 import 必须在类中有实际引用；生成代码后清理无用导入（用所在 IDE 的「Optimize Imports / 清理导入」菜单或命令功能，或命令行工具 Checkstyle/Spotless 自动去除；具体入口以个人 IDE 配置为准）
- ❌ 禁止复制粘贴残留 import：从别处拷贝代码时同步清理其 import，只保留当前类用到的

### 4. 声明规范

- 一行一个声明：`int a = 1; int b = 2;` → 拆两行
- 变量就近声明，使用时才声明
- `final`：可加 final 防误改（集合/常量/方法参数按需）

### 5. 比较与判空

```java
// 常量前置，防空指针
if ("SUCCESS".equals(status)) { }        // 正例
if (status.equals("SUCCESS")) { }        // 反例：status 为空 NPE

// 集合判空：用工具类
if (CollectionUtils.isEmpty(list)) { }   // 正例
if (list == null || list.size() == 0) { } // 可接受，但冗长

// 字符串判空
if (StringUtils.hasText(name)) { }       // 正例（Spring 工具）
```

### 6. 数值比较

- 整型包装类比较用 `equals` 或拆箱，禁 `==`（缓存范围外不等）

```java
Integer a = 200, b = 200;
if (a == b) { }      // 反例：-128~127 之外不等
if (a.equals(b)) { } // 正例
```

- 浮点比较不直接 `==`，用差值阈值

### 7. 集合与数组

- 优先泛型集合，避免裸类型
- 数组转列表注意 `Arrays.asList` 不可变：需增删用 `new ArrayList<>(Arrays.asList(...))`

## 反例 / 正例

```java
// 反例
public class Demo{
    private String name;
    public String getName(){return name;}
        public void setName(String name){this.name=name;}
}

// 正例
public class Demo {
    private String name;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

## 最佳实践

- 全程 IDE 自动格式化（Ctrl+Alt+L 类快捷键），提交前过一遍
- 团队统一 .editorconfig + Checkstyle/Spotless 插件，CI 校验格式，避免人工扯皮
- Lombok 减少样板代码（getter/setter/构造器），但业务逻辑不用 Lombok 简化
- 三目运算符嵌套超过 2 层改为 if/switch 或提取方法
- 长链式调用（LambdaQueryWrapper）超过 2 行时换行缩进

## 自检清单

- [ ] 4 空格缩进，无 Tab
- [ ] 行宽 ≤ 120
- [ ] 导入无通配符，分组有序，无未使用 import
- [ ] 方法间空 1 行，无多余空行
- [ ] 常量前置比较
- [ ] 包装类用 equals
- [ ] 无一行多声明
- [ ] 文件 UTF-8，结尾空行
