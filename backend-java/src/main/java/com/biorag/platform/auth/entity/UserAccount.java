package com.biorag.platform.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * 用户账号实体，对应数据库中的 business.users 表。
 */
@Entity
@Table(name = "users", schema = "business")
public class UserAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private UserStatus status;

    @ManyToMany
    @JoinTable(
            name = "user_roles",
            schema = "business",
            joinColumns = @JoinColumn(name = "user_id"),
            inverseJoinColumns = @JoinColumn(name = "role_id"))
    private Set<Role> roles = new LinkedHashSet<>();

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    /**
     * 供 JPA 从数据库记录还原对象时使用，业务代码不应直接调用。
     */
    protected UserAccount() {
    }

    /**
     * 创建一个默认处于启用状态的新用户账号。
     */
    public UserAccount(String email, String passwordHash) {
        this.email = Objects.requireNonNull(email, "email must not be null");
        this.passwordHash = Objects.requireNonNull(passwordHash, "passwordHash must not be null");
        this.status = UserStatus.ACTIVE;
    }

    /**
     * 停用当前账号，停用后的用户不能登录。
     */
    public void disable() {
        status = UserStatus.DISABLED;
    }

    /** 重新启用被管理员停用的账号。 */
    public void enable() {
        status = UserStatus.ACTIVE;
    }

    /** 为账号增加角色，重复添加时保持幂等。 */
    public void addRole(Role role) {
        roles.add(Objects.requireNonNull(role, "role must not be null"));
    }

    /** 移除指定角色。 */
    public void removeRole(Role role) {
        roles.remove(role);
    }

    /** 判断账号是否具有指定角色。 */
    public boolean hasRole(String code) {
        return roles.stream().anyMatch(role -> role.getCode().equals(code));
    }

    /**
     * 首次保存前写入创建时间和更新时间。
     */
    @PrePersist
    void beforeInsert() {
        Instant now = Instant.now();
        createdAt = now;
        updatedAt = now;
    }

    /**
     * 数据更新前刷新更新时间。
     */
    @PreUpdate
    void beforeUpdate() {
        updatedAt = Instant.now();
    }

    /** 返回用户唯一标识。 */
    public UUID getId() {
        return id;
    }

    /** 返回规范化后的邮箱。 */
    public String getEmail() {
        return email;
    }

    /** 返回不可逆的密码哈希。 */
    public String getPasswordHash() {
        return passwordHash;
    }

    /** 返回当前账号状态。 */
    public UserStatus getStatus() {
        return status;
    }

    /** 返回账号拥有的系统角色。 */
    public Set<Role> getRoles() {
        return Set.copyOf(roles);
    }

    /** 返回账号创建时间。 */
    public Instant getCreatedAt() {
        return createdAt;
    }

    /** 返回账号最后更新时间。 */
    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
