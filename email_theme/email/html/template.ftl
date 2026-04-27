<#macro emailLayout>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; background-color: #2f2f41 !important; margin: 0; padding: 0; }
        .email-container { max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #ddd; }
        .email-header { background-color: #1B263B; color: #ffffff; text-align: center; padding: 20px; }
        .email-body { padding: 30px; color: #333333; line-height: 1.5; }
        .email-footer { background-color: #f5f5f5; text-align: center; padding: 15px; font-size: 11px; color: #666666; }
        .button { display: inline-block; background-color: #007bff; color: #ffffff !important; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-weight: bold; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>ONSET-PACS</h1>
        </div>
        <div class="email-body">
            <#nested>
            
            <p>If you have any questions, contact Guillaume Theaud (guillaume.theaud.chum@ssss.gouv.qc.ca).</p>
            <p>Best regards,<br>The ONSET Team</p>
        </div>
        <div class="email-footer">
            <p><strong>Medical Disclaimer</strong><br>
            Content is for informational purposes only and not a substitute for professional medical advice. Reliance on any information provided is solely at your own risk.</p>
        </div>
    </div>
</body>
</html>
</#macro>
