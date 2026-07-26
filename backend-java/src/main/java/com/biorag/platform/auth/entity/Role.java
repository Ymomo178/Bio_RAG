package com.biorag.platform.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

/**
 * 系统角色实体，用于区分普通用户和管理员。
 */
@Entity
@Table(name = "roles", schema = "business")
public class Role {

    @Id
    private UUID id;

    @Column(nullable = false, unique = true, length = 32)
    private String code;

    @Column(nullable = false, length = 64)
    private String name;

    /** 供 JPA 还原角色记录。 */
    protected Role() {
    }

    /** 返回角色 ID。 */
    public UUID getId() {
        return id;
    }

    /** 返回稳定的角色代码。 */
    public String getCode() {
        return code;
    }

    /** 返回角色中文名称。 */
    public String getName() {
        return name;
    }
}
