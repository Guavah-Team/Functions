/**
 * @type {import('@types/aws-lambda').APIGatewayProxyHandler}
 * 
 * Next steps:
 * Check out sample function code generated in <project-dir>/amplify/backend/function/guavahApiTests/src
 * "amplify function build" builds all of your functions currently in the project
 * "amplify mock function <functionName>" runs your function locally
 * To access AWS resources outside of this Amplify app, edit the C:\Users\Jake Speyer\Desktop\Guavah\Functions\amplify\backend\function\guavahApiTests\custom-policies.json
 * "amplify push" builds all of your local backend resources and provisions them in the cloud
 * "amplify publish" builds all of your local backend and front-end resources (if you added hosting category) and provisions them in the cloud
 */
exports.handler = async (event) => {
    console.log(`EVENT: ${JSON.stringify(event)}`);
    return {
        statusCode: 200,
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        },
        body: JSON.stringify('Hello from Lambda!'),
    };
};
