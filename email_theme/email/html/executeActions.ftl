<#import "template.ftl" as layout>
<@layout.emailLayout>
    <p>Hello ${user.firstName!user.username},</p>
    
    <p>Your account has been created on the <strong>ONSET-PACS</strong> platform. To finalize your access, an administrator requires you to perform the following action(s):</p>
    
    <#-- Liste des actions requises -->
    <ul style="color: #1B263B; font-weight: bold;">
        <#list requiredActions as action>
            <li>${msg("requiredAction.${action}")}</li>
        </#list>
    </ul>

    <div style="background-color: #f4f4f9; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 6px;">
        <h4 style="margin-top: 0; color: #333;">Account Credentials</h4>
        <p style="margin: 5px 0;"><strong>Username:</strong> <span style="background: #eee; padding: 2px 5px; border-radius: 3px; font-family: monospace;">${user.username}</span></p>
        <p style="margin: 5px 0;"><strong>Associated Email:</strong> ${user.email}</p>
    </div>
    
    <p>Click the button below to complete these steps and access your workspace:</p>
    
    <div style="text-align: center; margin: 25px 0;">
        <a href="${link}" class="button">Setup My Account</a>
    </div>
    
    <p style="font-size: 12px; color: #777;">
        This secure link will expire in ${linkExpirationFormatter(linkExpiration)}.<br>
    </p>
</@layout.emailLayout>
