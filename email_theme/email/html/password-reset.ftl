<#import "template.ftl" as layout>
<@layout.emailLayout>
    <p>Hello ${user.firstName!user.username},</p>
    
    <p>A request has been made to reset your password for your ONSET-PACS account. Click the button below to choose a new one:</p>
    
    <a href="${link}" class="button">Reset Password</a>
    
    <p>This link will expire in ${linkExpiration} minutes.</p>
    <p>If you did not request this, you can safely ignore this email.</p>
</@layout.emailLayout>
