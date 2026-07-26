package com.biorag.platform.document.controller;

import com.biorag.platform.auth.service.SessionAuthenticationService;
import com.biorag.platform.document.service.ImageAssetService;
import jakarta.servlet.http.HttpSession;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 向已登录且有权限的用户返回检索证据原图。 */
@RestController
@RequestMapping("/api/assets")
public class ImageAssetController {
    private final ImageAssetService assets;
    private final SessionAuthenticationService authentication;

    /** 注入图片定位和 Session 认证服务。 */
    public ImageAssetController(ImageAssetService assets, SessionAuthenticationService authentication) {
        this.assets = assets;
        this.authentication = authentication;
    }

    /** 返回指定图片内容，浏览器可直接显示。 */
    @GetMapping("/{imageId}")
    ResponseEntity<FileSystemResource> get(@PathVariable String imageId, HttpSession session) {
        var asset = assets.find(authentication.requireUserId(session), imageId);
        MediaType mediaType = asset.contentType() == null ? MediaType.APPLICATION_OCTET_STREAM
                : MediaType.parseMediaType(asset.contentType());
        return ResponseEntity.ok().cacheControl(CacheControl.noCache()).contentType(mediaType)
                .body(new FileSystemResource(asset.path()));
    }
}
