# CRUD 完整示例

本文串联完整 CRUD 链路，展示各层规范落地效果。业务场景：商品（Product）管理。

## 分层文件一览

```
controller/ProductController.java
service/ProductService.java
service/impl/ProductServiceImpl.java
mapper/ProductMapper.java
entity/Product.java
dto/ProductCreateDTO.java
dto/ProductUpdateDTO.java
dto/ProductQueryDTO.java
vo/ProductVO.java
converter/ProductConverter.java
resources/mapper/ProductMapper.xml
```

## 1. Entity

```java
@TableName("t_product")
@Data
public class Product {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    /** 商品编号（唯一） */
    private String productNo;

    /** 商品名称 */
    private String name;

    /** 价格，单位：元 */
    private BigDecimal price;

    /** 库存 */
    private Integer stock;

    /** 状态：10-上架 20-下架 */
    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    @Version
    private Integer version;
}
```

## 2. Mapper

```java
@Mapper
public interface ProductMapper extends BaseMapper<Product> {
}
```

简单条件走 Wrapper，无需自定义方法。复杂查询再进 XML。

## 3. DTO

```java
@Data
public class ProductCreateDTO {
    @Schema(description = "商品名称")
    @NotBlank(message = "商品名称不能为空")
    @Size(max = 64, message = "名称过长")
    private String name;

    @Schema(description = "价格，单位：元")
    @NotNull(message = "价格不能为空")
    @DecimalMin(value = "0.01", message = "价格必须大于0")
    private BigDecimal price;

    @Schema(description = "库存")
    @NotNull(message = "库存不能为空")
    @Min(value = 0, message = "库存不能为负")
    private Integer stock;
}

@Data
public class ProductUpdateDTO {
    @Schema(description = "名称")
    @Size(max = 64, message = "名称过长")
    private String name;

    @Schema(description = "价格，单位：元")
    @DecimalMin(value = "0.01", message = "价格必须大于0")
    private BigDecimal price;

    @Schema(description = "库存")
    @Min(value = 0, message = "库存不能为负")
    private Integer stock;
}
```

## 4. VO

```java
@Data
public class ProductVO {
    @Schema(description = "主键 ID")
    private Long id;
    @Schema(description = "商品编号")
    private String productNo;
    @Schema(description = "商品名称")
    private String name;
    @Schema(description = "价格，单位：元")
    private BigDecimal price;
    @Schema(description = "库存")
    private Integer stock;
    @Schema(description = "状态编码")
    private Integer status;
    @Schema(description = "状态文案（由枚举填充）")
    private String statusText;
}
```

## 5. Converter（MapStruct）

```java
@Mapper(componentModel = "spring",
        unmappedTargetPolicy = ReportingPolicy.ERROR)
public interface ProductConverter {

    ProductVO toVO(Product product);

    Product toEntity(ProductCreateDTO createInfo);

    List<ProductVO> toVOList(List<Product> products);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createTime", ignore = true)
    @Mapping(target = "updateTime", ignore = true)
    @Mapping(target = "deleted", ignore = true)
    @Mapping(target = "version", ignore = true)
    void updateEntity(ProductUpdateDTO updateInfo, @MappingTarget Product product);
}
```

## 6. Service 接口

```java
public interface ProductService {

    ProductVO getById(Long id);

    Long create(ProductCreateDTO createInfo);

    void update(Long id, ProductUpdateDTO updateInfo);

    void delete(Long id);

    /** 扣减库存（乐观锁防超卖） */
    void deductStock(Long id, Integer delta);
}
```

## 7. ServiceImpl

```java
@Slf4j
@Service
@RequiredArgsConstructor
public class ProductServiceImpl implements ProductService {

    private final ProductMapper productMapper;
    private final ProductConverter productConverter;

    @Override
    public ProductVO getById(Long id) {
        return productConverter.toVO(getEntityOrThrow(id));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long create(ProductCreateDTO createInfo) {
        Product product = productConverter.toEntity(createInfo);
        product.setProductNo(buildProductNo());
        productMapper.insert(product);
        log.info("product created, id={}, productNo={}", product.getId(), product.getProductNo());
        return product.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(Long id, ProductUpdateDTO updateInfo) {
        Product product = getEntityOrThrow(id);
        productConverter.updateEntity(updateInfo, product);
        productMapper.updateById(product);
        log.info("product updated, id={}", id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        Product product = getEntityOrThrow(id);
        productMapper.deleteById(product.getId());
        log.info("product deleted, id={}", id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deductStock(Long id, Integer delta) {
        Product product = getEntityOrThrow(id);
        // 乐观锁条件更新：version 不匹配则影响行数为 0
        int rows = productMapper.update(null, new LambdaUpdateWrapper<Product>()
                .eq(Product::getId, id)
                .eq(Product::getVersion, product.getVersion())
                .ge(Product::getStock, delta)
                .setSql("stock = stock - " + delta)
                .setSql("version = version + 1"));
        if (rows == 0) {
            throw new BusinessException(ErrorCode.STOCK_NOT_ENOUGH, "库存不足或商品已变更，请重试");
        }
        log.info("product stock deducted, id={}, delta={}", id, delta);
    }

    private Product getEntityOrThrow(Long id) {
        Product product = productMapper.selectById(id);
        if (product == null) {
            throw new BusinessException(ErrorCode.PRODUCT_NOT_FOUND, "商品不存在或已删除");
        }
        return product;
    }

    private String buildProductNo() {
        return "P" + DateUtil.format(LocalDateTime.now(), "yyyyMMddHHmmss")
                + ThreadLocalRandom.current().nextInt(1000, 10000);
    }
}
```

> 注意：`deductStock` 用 `setSql` 拼接**固定 SQL 片段**（无外部输入），安全；若拼接外部输入必须参数化。团队更严格时改用 XML `SET stock = stock - #{delta}`。

## 8. Controller

```java
@Tag(name = "商品管理", description = "商品的查询、创建、更新、删除")
@Slf4j
@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
@Validated
public class ProductController {

    private final ProductService productService;

    @Operation(summary = "查询商品详情", description = "按 ID 查询商品")
    @GetMapping("/{id}")
    public Response<ProductVO> getById(@PathVariable @NotNull Long id) {
        log.info("product getById start, id={}", id);
        return Response.success(productService.getById(id));
    }

    @Operation(summary = "创建商品", description = "创建商品，返回商品 ID")
    @PostMapping
    public Response<Long> create(@Validated @RequestBody ProductCreateDTO createInfo) {
        return Response.success(productService.create(createInfo));
    }

    @Operation(summary = "更新商品", description = "按 ID 更新商品")
    @PutMapping("/{id}")
    public Response<Void> update(@PathVariable Long id,
                               @Validated @RequestBody ProductUpdateDTO updateInfo) {
        productService.update(id, updateInfo);
        return Response.success();
    }

    @Operation(summary = "删除商品", description = "按 ID 删除商品")
    @DeleteMapping("/{id}")
    public Response<Void> delete(@PathVariable Long id) {
        productService.delete(id);
        return Response.success();
    }
}
```

## 9. 建表 DDL

```sql
CREATE TABLE `t_product` (
    `id`          BIGINT       NOT NULL COMMENT '主键ID（雪花）',
    `product_no`  VARCHAR(32)  NOT NULL COMMENT '商品编号',
    `name`        VARCHAR(64)  NOT NULL COMMENT '商品名称',
    `price`       DECIMAL(10,2) NOT NULL COMMENT '价格（元）',
    `stock`       INT          NOT NULL DEFAULT 0 COMMENT '库存',
    `status`      TINYINT      NOT NULL DEFAULT 10 COMMENT '状态：10-上架 20-下架',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0-未删 1-已删',
    `version`     INT          NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_product_no` (`product_no`),
    KEY `idx_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '商品表';
```

## 规范对照

| 规范点 | 落地位置 |
|---|---|
| 构造器注入 | ProductServiceImpl final 字段 + @RequiredArgsConstructor |
| 事务 rollbackFor | 写方法 @Transactional(rollbackFor = Exception.class) |
| 乐观锁 | deductStock 版本条件更新 |
| 统一错误码 | BusinessException(ErrorCode.XXX, msg) |
| MapStruct 转换 | ProductConverter，无手写 get/set |
| 校验注解 | DTO 字段 @NotBlank/@DecimalMin/@Min |
| OpenAPI 注解 | Controller @Tag/@Operation + DTO/VO 字段 @Schema（依赖 springdoc，见 build-standards） |
| 日志占位符 | log.info 带业务 ID；全类 @Slf4j（Controller/ServiceImpl） |
| 逻辑删除 | @TableLogic + deleted 列 |
