# 代码格式规范 (Code Format Standards)

## 适用范围

生成任意 Java 代码前必读。规范缩进、换行、空行、导入、常见语法陷阱。实际格式化以团队 IDE 配置（.editorconfig / Checkstyle / Spotless）为准，本文档为生成代码时的基准。

## 强制规则

### 1. 基础格式

- 缩进：4 空格，禁止 Tab（IDE 配置展开 Tab）
- 行宽：120 字符以内（团队配置为准）
- 编码：UTF-8，换行符 LF
- 文件结尾保留一个空行
- 行尾不留空白字符（空格 / Tab 收尾一律删除）
- 每个源文件必须声明 `package`，禁止默认包
- `package` 与 `import` 声明不换行（一行写完整）

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
- ❌ 禁止导入 JDK 内部 API（`sun.*`、`com.sun.*`）——跨 JDK 版本不可移植

### 4. 声明规范

- 一行一个声明：`int a = 1; int b = 2;` → 拆两行
- 一行一条语句：`a = 1; b = 2;` → 拆两行
- 变量就近声明，使用时才声明
- `final`：可加 final 防误改（集合/常量/方法参数按需）
- 修饰符顺序固定：`public / protected / private / abstract / static / final`（如 `public static final`，不写 `static public final`）
- 禁冗余修饰符：接口方法默认 `public abstract`，不再显式写；接口常量默认 `public static final`，不重复写
- 数组类型写法：`int[] numbers`（`[]` 紧跟元素类型），不写 C 风格 `int numbers[]`
- `long` 字面量用大写 `L`：`3000L`（小写 `l` 与数字 `1` 易混）
- 一个源文件只允许一个顶层类（`public` 类名与文件名一致；辅助类放独立文件或作为嵌套类）

### 5. 比较与判空

- 字符串比较一律用 `equals`，禁止 `==`（`==` 比较的是引用地址，字符串内容相同时也可能不等）

```java
// 常量前置，防空指针
if ("SUCCESS".equals(status)) { }        // 正例
if (status.equals("SUCCESS")) { }        // 反例：status 为空 NPE
if (status == "SUCCESS") { }             // 反例：字符串不该用 == 比较

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

### 8. 空格与花括号

**空格**（运算符、关键字、逗号分号）

- 运算符与关键字两侧留空格：`a == b`、`i < n`、`if (x)`
- 逗号、分号后留空格：`method(a, b, c)`、`for (int i = 0; i < n; i++)`
- 反例：`if(x)`、`a==b`、`method(a,b,c)`

**花括号**

- `if / for / while / do` 等控制语句即使只有一条语句，也必须加 `{}`
- 左花括号 `{` 跟在行尾（K&R 风格），不另起一行
- `} else {`、`} catch (...) {`、`} finally {` 写在同一行

```java
// 反例
if (x)
    doSomething();        // 缺 {}
if (x)
{                         // { 另起一行
    doSomething();
}

// 正例
if (x) {
    doSomething();
} else {
    doOther();
}

for (int i = 0; i < n; i++) {   // 运算符两侧有空格，{ 在行尾
    sum += i;
}
```

### 9. 日志与其他书写卫生

- 禁止 `System.out` / `System.err` 直接输出，统一使用日志框架记录
- 禁止 `e.printStackTrace()`，异常统一 `log.error(..., e)` 记录（带堆栈）
- 遗留标记 `TODO` / `FIXME` 不得留在交付代码里；**唯一例外**是流程要求的收敛标记 `// TODO(收敛)`（用于"发现任务外重复逻辑、暂不抽取、留待需求覆盖阶段统一处理"，见 ai-dev-workflow），该标记允许保留

```java
log.info("订单处理完成, orderId={}", orderId);   // 正例：日志框架
System.out.println("订单处理完成");               // 反例：System.out
e.printStackTrace();                              // 反例：打印堆栈
```

> `System.out/err`、`printStackTrace` 的完整规则见 logging 规范；本节只做格式侧提示，避免与 logging 规范重复。

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
- **本仓提供可直接引用的格式化配置**：`assets/eclipse-formatter.xml`（Eclipse JDT profile，4 空格/K&R/120）——配 Spotless 后 `mvn spotless:apply` 一键格式化（引法见 build-standards `standards/maven-standards.md`）
- Lombok 减少样板代码（getter/setter/构造器），但业务逻辑不用 Lombok 简化
- 三目运算符嵌套超过 2 层改为 if/switch 或提取方法
- 长链式调用（LambdaQueryWrapper）超过 2 行时换行缩进

## 自检清单

- [ ] 4 空格缩进，无 Tab
- [ ] 行宽 ≤ 120
- [ ] 导入无通配符，分组有序，无未使用 import，无 `sun.*` / `com.sun.*`
- [ ] 方法间空 1 行，无多余空行
- [ ] 常量前置比较；字符串比较用 `equals`（非 `==`）
- [ ] 包装类用 equals
- [ ] 无一行多声明；无一行多语句
- [ ] 文件 UTF-8，结尾空行，行尾无空白
- [ ] package 已声明；package / import 未换行
- [ ] 修饰符顺序正确，无冗余修饰符
- [ ] 数组 `int[] a`；`long` 用大写 `L`；一文件一顶层类
- [ ] 运算符 / 关键字 / 逗号后空格正确
- [ ] `if / for / while` 均带 `{}`；花括号 K&R；`} else` 同行
- [ ] 无 `System.out` / `System.err`、无 `printStackTrace`；`TODO` 仅允许 `TODO(收敛)`
